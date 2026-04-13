from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

FIELD_LABELS: dict[str, str] = {
    "title": "标题",
    "time": "发布时间",
    "content": "正文",
}


def show_header() -> None:
    console.print(Panel.fit(
        "[bold cyan]网页标记工具[/bold cyan]\n"
        "[dim]引导你从列表页提取文章结构，生成 spider 配置[/dim]",
        border_style="cyan",
    ))
    console.print()


@contextmanager
def show_spinner(message: str) -> Generator[None, None, None]:
    with console.status(f"[cyan]{message}[/cyan]"):
        yield


def show_candidates_table(field_name: str, candidates: list[dict[str, Any]]) -> None:
    label = FIELD_LABELS.get(field_name, field_name)
    table = Table(
        title=f"[bold]{label}候选[/bold]",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("序号", style="dim", width=4, justify="right")
    table.add_column("预览文本", max_width=60)
    table.add_column("评分", justify="right", width=6)

    for i, cand in enumerate(candidates, 1):
        table.add_row(
            str(i),
            str(cand.get("preview", "")),
            str(cand.get("score", "")),
        )

    console.print(table)
    console.print()


def show_link_candidates_table(candidates: list[dict[str, Any]]) -> None:
    table = Table(
        title="[bold]文章链接候选组[/bold]",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("序号", style="dim", width=4, justify="right")
    table.add_column("链接数", justify="right", width=6)
    table.add_column("示例内容（前3条）", max_width=65)

    for i, cand in enumerate(candidates, 1):
        link_count = str(cand.get("text_len", "?"))
        matched = cand.get("title_matched", False)
        badge = " [bold yellow]★ 标题匹配[/bold yellow]" if matched else ""
        sample_links: list[dict[str, str]] = cand.get("sample_links", [])
        if sample_links:
            lines = [
                f"[green]{s['text'] or '(无文本)'}[/green]\n[dim]{s['href']}[/dim]"
                for s in sample_links
            ]
            preview_text = "\n\n".join(lines) + badge
        else:
            preview_text = str(cand.get("preview", "")) + badge
        table.add_row(str(i), link_count, preview_text)

    console.print(table)
    console.print()


def show_confirmed_summary(confirmed: dict[str, str]) -> None:
    lines = []
    label_map = {
        "list_link_selector": "列表链接选择器",
        "title_selector": "标题选择器",
        "time_selector": "时间选择器",
        "content_selector": "正文选择器",
    }
    for key, val in confirmed.items():
        label = label_map.get(key, key)
        lines.append(f"[bold]{label}[/bold]: [green]{val}[/green]")

    console.print(Panel(
        "\n".join(lines),
        title="[bold green]已确认的选择器[/bold green]",
        border_style="green",
    ))
    console.print()


def show_next_steps(output_path: str) -> None:
    console.print(Panel(
        f"[bold]marker.json[/bold] 已保存到：[cyan]{output_path}[/cyan]\n\n"
        "下一步：在 Claude Code 中运行 [bold]spider-authoring[/bold] skill，\n"
        "它会读取这个文件并自动生成爬虫代码。",
        title="[bold cyan]完成！[/bold cyan]",
        border_style="cyan",
    ))


def show_error(message: str) -> None:
    console.print(Panel(
        f"[red]{message}[/red]",
        title="[bold red]错误[/bold red]",
        border_style="red",
    ))
    console.print()
