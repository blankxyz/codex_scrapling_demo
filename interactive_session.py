from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import questionary

from demo_marker_extractor import fetch_html, analyze_html, _build_prompt, find_selector_by_text
from ui import (
    show_header,
    show_spinner,
    show_api_candidates_table,
    show_link_candidates_table,
    show_confirmed_summary,
    show_next_steps,
    show_error,
    console,
)

_MANUAL = "__manual__"
_SKIP = "__skip__"
_MANUAL_TEXT = "__manual_text__"


def _pick_field_candidate(field_label: str, candidates: list[dict[str, Any]], html: str) -> str | None:
    """展示字段候选列表，让用户选择或粘贴文字反查。返回 CSS 选择器字符串，或 None（跳过）。"""
    if not candidates:
        console.print(f"[yellow]未找到{field_label}候选，跳过。[/yellow]")
        return None

    choices = [
        questionary.Choice(
            title=f"[{i+1}] {c.get('preview', '')}",
            value=c["selector"],
        )
        for i, c in enumerate(candidates)
    ]
    choices.append(questionary.Choice(title="手动输入（从网页复制文字）", value=_MANUAL_TEXT))
    choices.append(questionary.Choice(title="跳过此字段", value=_SKIP))

    result = questionary.select(
        f"请选择【{field_label}】对应的内容：",
        choices=choices,
    ).ask()

    if result is None or result == _SKIP:
        return None

    if result == _MANUAL_TEXT:
        while True:
            pasted = questionary.text(
                f"请从网页上复制【{field_label}】的文字，粘贴到这里："
            ).ask()
            if not pasted:
                return None
            sel = find_selector_by_text(html, pasted.strip())
            if sel:
                console.print(f"[green]已定位选择器：{sel}[/green]")
                return sel
            console.print("[yellow]未在页面中找到该文字，请重试或选择跳过。[/yellow]")
            retry = questionary.confirm("重新输入？").ask()
            if not retry:
                return None

    return result


def _save_and_exit(final_marker: dict, site_slug: str, url: str, out_dir: Path) -> None:
    marker_path = out_dir / "marker.json"
    prompt_path = out_dir / "codex_prompt.txt"
    marker_path.write_text(json.dumps(final_marker, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt_path.write_text(_build_prompt(url, site_slug, final_marker), encoding="utf-8")
    show_next_steps(str(marker_path))


def _pick_link_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    choices = [
        questionary.Choice(
            title=f"[{i+1}] {c['selector']}  ({c.get('text_len', '?')} 条链接)",
            value=c,
        )
        for i, c in enumerate(candidates)
    ]
    choices.append(questionary.Choice(title="手动输入 CSS 选择器", value=_MANUAL))

    result = questionary.select(
        "请选择文章链接所在的候选组：",
        choices=choices,
    ).ask()

    if result is None:
        return None
    if result == _MANUAL:
        manual = questionary.text("请输入 CSS 选择器（如 ul.news-list a）：").ask()
        if not manual:
            return None
        return {"selector": manual.strip(), "sample_links": [], "text_len": 0}
    return result


class InteractiveSession:
    def run(self, url: str, render: str = "auto", max_candidates: int = 4, title_hint: str = "") -> dict[str, Any]:
        show_header()

        console.rule("[bold cyan]分析列表页[/bold cyan]")
        console.print()

        try:
            with show_spinner(f"正在抓取：{url}"):
                html, xhr_responses, fetch_meta = fetch_html(url, render=render)
        except Exception as exc:
            show_error(f"抓取失败：{exc}\n\n建议使用 --render dynamic 重试。")
            raise SystemExit(1)

        result = analyze_html(html, url, fetch_meta, xhr_responses=xhr_responses,
                              max_candidates=max_candidates, title_hint=title_hint)
        marker = result["marker"]
        site_slug = marker["site_slug"]
        out_dir = Path("out") / site_slug
        out_dir.mkdir(parents=True, exist_ok=True)

        # ── API 优先分支 ──────────────────────────────────────────────
        api_candidates = marker.get("api_candidates", [])
        if api_candidates:
            console.rule("[bold green]发现 API 接口[/bold green]")
            show_api_candidates_table(api_candidates)
            use_api = questionary.confirm("检测到 API 接口，是否使用 API 模式（推荐）？").ask()
            if use_api:
                if len(api_candidates) == 1:
                    chosen_api = api_candidates[0]
                else:
                    choices = [
                        questionary.Choice(title=f"[{i+1}] {c['url']}", value=c)
                        for i, c in enumerate(api_candidates)
                    ]
                    chosen_api = questionary.select("请选择要使用的 API：", choices=choices).ask()
                    if chosen_api is None:
                        console.print("[yellow]已取消。[/yellow]")
                        raise SystemExit(0)

                final_marker: dict = {
                    "site_slug": site_slug,
                    "list_url": url,
                    "mode": "api",
                    "api_endpoint": chosen_api["url"],
                    "api_preview": chosen_api.get("preview", ""),
                    "requires_dynamic": False,
                }
                ok = questionary.confirm("保存 marker.json？").ask()
                if not ok:
                    console.print("[yellow]已取消，未保存。[/yellow]")
                    raise SystemExit(0)
                _save_and_exit(final_marker, site_slug, url, out_dir)
                return final_marker

        # ── CSS 选择器流程（fallback）────────────────────────────────
        if marker["page_type"] != "list_or_index":
            console.print(f"[yellow]⚠ 检测到页面类型为 '{marker['page_type']}'，不像列表页。[/yellow]")
            ok = questionary.confirm("仍要继续？").ask()
            if not ok:
                raise SystemExit(0)

        link_candidates = marker.get("list_link_candidates", [])
        if not link_candidates:
            show_error("未找到任何链接候选。请检查 URL 是否为列表页，或使用 --render dynamic。")
            raise SystemExit(1)

        show_link_candidates_table(link_candidates)
        chosen = _pick_link_candidate(link_candidates)
        if chosen is None:
            console.print("[yellow]已取消。[/yellow]")
            raise SystemExit(0)

        list_link_selector = chosen["selector"]
        sample_links: list[dict[str, str]] = chosen.get("sample_links", [])
        detail_sample_url = urljoin(url, sample_links[0]["href"]) if sample_links else ""

        confirmed: dict[str, str] = {"list_link_selector": list_link_selector}
        show_confirmed_summary(confirmed)

        # ── 详情页分析 ────────────────────────────────────────────────
        detail_html = ""
        if detail_sample_url:
            console.rule("[bold cyan]分析详情页字段[/bold cyan]")
            try:
                with show_spinner(f"正在抓取详情页样本：{detail_sample_url}"):
                    # detail_html 仅用于 CSS 候选分析，详情页无需 API 检测，故丢弃 xhr_responses
                    detail_html, _, detail_fetch_meta = fetch_html(detail_sample_url, render=render)
                detail_result = analyze_html(detail_html, detail_sample_url, detail_fetch_meta)
                detail_marker = detail_result["marker"]
            except Exception as exc:
                console.print(f"[yellow]详情页抓取失败：{exc}，跳过字段分析。[/yellow]")
            else:
                field_map = [
                    ("title", "标题", "title_candidates"),
                    ("time", "时间", "time_candidates"),
                    ("content", "正文", "content_candidates"),
                    ("author", "作者", "author_candidates"),
                ]
                detail_confirmed: dict[str, str] = {}
                for field_key, field_label, cand_key in field_map:
                    candidates = detail_marker.get(cand_key, [])
                    sel = _pick_field_candidate(field_label, candidates, detail_html)
                    if sel:
                        detail_confirmed[f"{field_key}_selector"] = sel

                if detail_confirmed:
                    confirmed.update(detail_confirmed)
                    show_confirmed_summary(confirmed)

        ok = questionary.confirm("保存 marker.json？").ask()
        if not ok:
            console.print("[yellow]已取消，未保存。[/yellow]")
            raise SystemExit(0)

        requires_dynamic = fetch_meta.get("engine", "") == "scrapling.DynamicFetcher"
        final_marker = {
            "site_slug": site_slug,
            "list_url": url,
            "mode": "css",
            "list_link_selector": list_link_selector,
            "detail_sample_url": detail_sample_url,
            "sample_links": sample_links,
            "requires_dynamic": requires_dynamic,
            "confirmed": confirmed,
        }

        _save_and_exit(final_marker, site_slug, url, out_dir)

        # ── 衔接 Codex 生成爬虫 ─────────────────────────────────
        console.print()
        run_codex = questionary.confirm("是否立即调用 Codex 生成爬虫并抓取？").ask()
        if run_codex:
            script = Path(__file__).resolve().parent / "codex_spider_run_template.sh"
            if not script.exists():
                show_error(f"未找到模板脚本：{script}")
                return final_marker
            cmd = [
                str(script),
                "--site-slug", site_slug,
                "--list-url", url,
                "--marker", str(out_dir / "marker.json"),
            ]
            console.rule("[bold cyan]启动 Codex Spider Run[/bold cyan]")
            sys.exit(subprocess.call(cmd))

        return final_marker
