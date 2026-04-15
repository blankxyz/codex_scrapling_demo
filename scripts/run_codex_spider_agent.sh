#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <site_slug> <list_url> <template_json> [model] [max_repair_rounds]" >&2
  exit 1
fi

SITE_SLUG="$1"
LIST_URL="$2"
TEMPLATE_JSON="$3"
MODEL="${4:-}"
MAX_REPAIR="${5:-2}"

CMD=(python3 -m codex_spider_tool.agent_runner
  --site-slug "$SITE_SLUG"
  --list-url "$LIST_URL"
  --template-json "$TEMPLATE_JSON"
  --max-repair-rounds "$MAX_REPAIR")

if [ -n "$MODEL" ]; then
  CMD+=(--model "$MODEL")
fi

"${CMD[@]}"
