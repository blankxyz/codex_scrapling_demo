from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import questionary

from demo_marker_extractor import fetch_html, analyze_html, _build_prompt
from ui import (
    show_header,
    show_spinner,
    show_link_candidates_table,
    show_confirmed_summary,
    show_next_steps,
    show_error,
    console,
)

_MANUAL = "__manual__"


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
                html, fetch_meta = fetch_html(url, render=render)
        except Exception as exc:
            show_error(f"抓取失败：{exc}\n\n建议使用 --render dynamic 重试。")
            raise SystemExit(1)

        result = analyze_html(html, url, fetch_meta, max_candidates=max_candidates, title_hint=title_hint)
        marker = result["marker"]

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

        ok = questionary.confirm("保存 marker.json？").ask()
        if not ok:
            console.print("[yellow]已取消，未保存。[/yellow]")
            raise SystemExit(0)

        site_slug = marker["site_slug"]
        requires_dynamic = fetch_meta.get("engine", "") == "scrapling.DynamicFetcher"
        final_marker: dict[str, Any] = {
            "site_slug": site_slug,
            "list_url": url,
            "list_link_selector": list_link_selector,
            "detail_sample_url": detail_sample_url,
            "sample_links": sample_links,
            "requires_dynamic": requires_dynamic,
        }

        out_dir = Path("out") / site_slug
        out_dir.mkdir(parents=True, exist_ok=True)
        marker_path = out_dir / "marker.json"
        prompt_path = out_dir / "codex_prompt.txt"

        marker_path.write_text(json.dumps(final_marker, ensure_ascii=False, indent=2), encoding="utf-8")
        prompt_path.write_text(_build_prompt(url, site_slug, final_marker), encoding="utf-8")

        show_next_steps(str(marker_path))

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
                "--marker", str(marker_path),
            ]
            console.rule("[bold cyan]启动 Codex Spider Run[/bold cyan]")
            sys.exit(subprocess.call(cmd))

        return final_marker
