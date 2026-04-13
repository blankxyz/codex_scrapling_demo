#!/usr/bin/env bash
set -euo pipefail

# Reusable Codex exec template for spider generation + crawl.
#
# Usage:
#   ./codex_spider_run_template.sh \
#     --site-slug henan-gov-cn \
#     --list-url https://gd.henan.gov.cn/sy/tz/ \
#     --marker out/henan-gov-cn/marker.json \
#     --schema schemas/news_article.schema.json \
#     --spider spiders/henan-gov-cn.py \
#     --test tests/test_henan-gov-cn.py \
#     --output out/henan-gov-cn/crawl_results.json

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SITE_SLUG=""
LIST_URL=""
MARKER_PATH=""
SCHEMA_PATH="schemas/news_article.schema.json"
SPIDER_PATH=""
TEST_PATH=""
OUTPUT_PATH=""

usage() {
  cat <<EOF
用法: $0 --site-slug <slug> --list-url <url> --marker <path> [选项]

必选参数:
  --site-slug   站点标识（如 henan-gov-cn）
  --list-url    列表页入口 URL
  --marker      marker.json 文件路径

可选参数:
  --schema      统一文章 schema 路径（默认 schemas/news_article.schema.json）
  --spider      输出 spider 文件路径（默认 spiders/<site-slug>.py）
  --test        输出测试文件路径（默认 tests/test_<site-slug>.py）
  --output      爬取结果 JSON 路径（默认 out/<site-slug>/crawl_results.json）
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --site-slug) SITE_SLUG="$2"; shift 2 ;;
    --list-url)  LIST_URL="$2";  shift 2 ;;
    --marker)    MARKER_PATH="$2"; shift 2 ;;
    --schema)    SCHEMA_PATH="$2"; shift 2 ;;
    --spider)    SPIDER_PATH="$2"; shift 2 ;;
    --test)      TEST_PATH="$2"; shift 2 ;;
    --output)    OUTPUT_PATH="$2"; shift 2 ;;
    -h|--help)   usage ;;
    *)           echo "未知参数: $1" >&2; usage ;;
  esac
done

# 校验必选参数
[[ -z "$SITE_SLUG" ]] && { echo "错误: 缺少 --site-slug" >&2; usage; }
[[ -z "$LIST_URL"  ]] && { echo "错误: 缺少 --list-url"  >&2; usage; }
[[ -z "$MARKER_PATH" ]] && { echo "错误: 缺少 --marker"  >&2; usage; }
[[ -f "$MARKER_PATH" ]] || { echo "错误: marker 文件不存在: $MARKER_PATH" >&2; exit 1; }

# 填充默认路径
SPIDER_PATH="${SPIDER_PATH:-spiders/${SITE_SLUG}.py}"
TEST_PATH="${TEST_PATH:-tests/test_${SITE_SLUG}.py}"
OUTPUT_PATH="${OUTPUT_PATH:-out/${SITE_SLUG}/crawl_results.json}"

# 确保输出目录存在
mkdir -p "$(dirname "$SPIDER_PATH")" "$(dirname "$TEST_PATH")" "$(dirname "$OUTPUT_PATH")"

echo "=== Codex Spider Run ==="
echo "站点:   ${SITE_SLUG}"
echo "列表页: ${LIST_URL}"
echo "Marker: ${MARKER_PATH}"
echo "Spider: ${SPIDER_PATH}"
echo "测试:   ${TEST_PATH}"
echo "输出:   ${OUTPUT_PATH}"
echo "========================"
echo

cat <<PROMPT | codex exec --cd "$ROOT_DIR" --skip-git-repo-check -
Use the spider-authoring skill.

Read:
- $MARKER_PATH
- $SCHEMA_PATH

Then do end-to-end:
1) Generate/update spider at $SPIDER_PATH. Check the marker's "requires_dynamic" field: if true, use DynamicFetcher; otherwise prefer Fetcher. Use fallback selectors.
2) Generate/update tests at $TEST_PATH.
3) Run the spider to crawl the full list from $LIST_URL.
4) Save all extracted items to $OUTPUT_PATH.
5) Print summary: total_links, success_count, error_count, output file path.

Additional constraints:
- If the marker contains a "list_link_selector" field, use it as the primary selector for extracting article links from the list page.
- Keep output fields aligned with the unified schema.
- Save fixtures for regression testing when needed.
- For detail URLs on the same host, normalize to https if http redirects cause fetch errors.

Context:
- site_slug: $SITE_SLUG
PROMPT
