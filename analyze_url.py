#!/usr/bin/env python3
from __future__ import annotations

import argparse

from interactive_session import InteractiveSession


def main() -> None:
    parser = argparse.ArgumentParser(
        description="交互式分析列表页，引导生成 marker.json"
    )
    parser.add_argument("url", help="列表页 URL")
    parser.add_argument(
        "--render",
        choices=["auto", "static", "dynamic"],
        default="auto",
        help="渲染模式（默认 auto）",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=4,
        metavar="N",
        help="每个字段最多展示 N 个候选（默认 4）",
    )
    parser.add_argument(
        "--title",
        default="",
        help="提供一个已知的文章标题，用于辅助识别正确的链接候选组",
    )
    args = parser.parse_args()

    try:
        InteractiveSession().run(
            url=args.url,
            render=args.render,
            max_candidates=args.max_candidates,
            title_hint=args.title,
        )
    except KeyboardInterrupt:
        print("\n已取消。")


if __name__ == "__main__":
    main()
