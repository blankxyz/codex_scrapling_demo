#!/usr/bin/env bash
set -euo pipefail

# ── Prefect 直出全自动 Pipeline ──
# 分析列表页 → 直接生成 Prefect flow → 注册到目标仓库 → 可选本地执行
#
# 用法:
#   ./run_pipeline_all.sh <list-url> [选项]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MODEL=""
ANALYSIS_SANDBOX="danger-full-access"
SANDBOX="danger-full-access"
NO_RUN=false
HEADLESS=true
URL=""
SLUG_OVERRIDE=""
DEPLOY_REPO="/home/blank/playground/prefect_demo"

slug_from_url() {
  local url="$1"
  local hostpath="${url#*://}"
  hostpath="${hostpath%%\?*}"
  hostpath="${hostpath%%#*}"
  hostpath="${hostpath%/}"
  local slug
  slug=$(echo "$hostpath" | tr '/._:' '-' | tr -s '-' | sed 's/^-//;s/-$//')
  echo "${slug:0:60}"
}

insert_registry_entry() {
  local registry_file="$1"
  local entry="$2"
  local flow_name="$3"
  local slug="$4"
  local tmpfile

  if grep -qF "$entry" "$registry_file"; then
    echo "  registry.yaml 已包含 $entry，跳过"
    return 0
  fi

  tmpfile=$(mktemp)
  cat >"$tmpfile" <<EOF

  - entrypoint: ${entry}
    name: ${flow_name}
    interval: 86400
    description: ${slug} 自动生成爬虫
    tags: [auto-generated]
EOF

  sed -i "/^# 平台工具 flow/r $tmpfile" "$registry_file"
  rm -f "$tmpfile"
  echo "  已注册到 registry.yaml: $entry"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    --sandbox) SANDBOX="$2"; ANALYSIS_SANDBOX="$2"; shift 2 ;;
    --analysis-sandbox) ANALYSIS_SANDBOX="$2"; shift 2 ;;
    --slug) SLUG_OVERRIDE="$2"; shift 2 ;;
    --deploy-repo) DEPLOY_REPO="$2"; shift 2 ;;
    --no-run) NO_RUN=true; shift ;;
    --no-headless) HEADLESS=false; shift ;;
    -h|--help)
      cat <<'HELP'
用法: run_pipeline_all.sh <list-url> [选项]

全自动 Pipeline：分析 → 直接生成 Prefect flow → 注册 → 提交

参数:
  <list-url>                 要分析的列表页 URL

选项:
  --slug <slug>              手动指定爬虫标识，覆盖自动生成的值
  --deploy-repo <path>       目标 Prefect 仓库路径
                             默认: /home/blank/playground/prefect_demo
  --model <model>            Codex 使用的模型
  --sandbox <mode>           全流程统一 Sandbox 模式
  --analysis-sandbox <mode>  Step 1 分析专用 Sandbox 模式
                             默认: danger-full-access
  --no-run                   跳过最后的 Prefect spider 本地执行
  --no-headless              Chrome 使用有头模式（默认无头）
  -h, --help                 显示帮助

流程:
  Step 1  分析列表页结构，输出 analysis_outputs/<slug>_analysis.json
  Step 2  直接输出 Prefect spider 到目标仓库 spiders/<slug>_spider.py
  Step 3  在目标仓库注册到 registry.yaml 并 git commit
  Step 4  可选本地执行目标仓库中的 spider 文件

示例:
  ./run_pipeline_all.sh https://www.nxnews.net/sh/jjcz/
  ./run_pipeline_all.sh https://example.com/news/ --slug old-slug
  ./run_pipeline_all.sh https://example.com/news/ --deploy-repo /path/to/prefect_demo --no-run
HELP
      exit 0
      ;;
    *)
      if [[ -z "$URL" ]]; then
        URL="$1"
        shift
      else
        echo "错误: 未知参数 '$1'" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "错误: 请提供列表页 URL" >&2
  echo "运行 $0 --help 查看详细帮助" >&2
  exit 1
fi

if [[ -n "$SLUG_OVERRIDE" ]]; then
  SLUG="$SLUG_OVERRIDE"
else
  SLUG=$(slug_from_url "$URL")
fi

if [[ ! -d "$DEPLOY_REPO" ]]; then
  echo "错误: 目标仓库不存在: $DEPLOY_REPO" >&2
  exit 1
fi

if [[ ! -f "$DEPLOY_REPO/spiders/registry.yaml" ]]; then
  echo "错误: 未找到目标 registry 文件: $DEPLOY_REPO/spiders/registry.yaml" >&2
  exit 1
fi

echo "═══════════════════════════════════════════"
echo "  Pipeline: $URL"
echo "  Slug:     $SLUG"
echo "  Analysis sandbox: $ANALYSIS_SANDBOX"
echo "  Other steps:      $SANDBOX"
echo "  Deploy repo:      $DEPLOY_REPO"
echo "═══════════════════════════════════════════"

ANALYSIS_CODEX_ARGS=(-s "$ANALYSIS_SANDBOX")
CODEX_ARGS=(-s "$SANDBOX")
RETRY_CODEX_ARGS=(-s danger-full-access)
if [[ -n "$MODEL" ]]; then
  ANALYSIS_CODEX_ARGS+=(-m "$MODEL")
  CODEX_ARGS+=(-m "$MODEL")
  RETRY_CODEX_ARGS+=(-m "$MODEL")
fi

CDP_URL="${CHROME_CDP_URL:-http://127.0.0.1:9222}"
CDP_PORT="${CHROME_CDP_PORT:-9222}"
CDP_PID=""

echo ""
echo "▶ 关闭已有的 Chrome CDP 进程 ..."
if lsof -ti :"$CDP_PORT" >/dev/null 2>&1; then
  lsof -ti :"$CDP_PORT" | xargs kill 2>/dev/null || true
  sleep 1
fi

echo "▶ 启动新的 Chrome CDP ..."
CHROME_HEADLESS="$HEADLESS" "$SCRIPT_DIR/start_chrome_cdp.sh" &
CDP_PID=$!
trap 'kill "$CDP_PID" 2>/dev/null || true' EXIT INT TERM

echo -n "  等待 CDP 就绪 "
for i in $(seq 1 15); do
  if curl -sf "${CDP_URL}/json/version" >/dev/null 2>&1; then
    echo " OK"
    break
  fi
  echo -n "."
  sleep 1
done

if ! curl -sf "${CDP_URL}/json/version" >/dev/null 2>&1; then
  echo ""
  echo "错误: Chrome CDP 启动超时，请检查 Chrome 安装" >&2
  kill "$CDP_PID" 2>/dev/null || true
  exit 1
fi
echo "  CDP 就绪 (PID: $CDP_PID)"

echo ""
echo "═══════════════════════════════════════════"
echo "  Step 1/4: 分析列表页"
echo "═══════════════════════════════════════════"

ANALYSIS_PROMPT="使用当前目录的 \$scrapling-spider-analysis 分析这个列表页，并把结果输出到 analysis_outputs/${SLUG}_analysis.json：${URL}"
codex exec "${ANALYSIS_CODEX_ARGS[@]}" "$ANALYSIS_PROMPT"

ANALYSIS_JSON="analysis_outputs/${SLUG}_analysis.json"
if [[ ! -f "$ANALYSIS_JSON" ]]; then
  echo "错误: 未找到本次分析结果 $ANALYSIS_JSON" >&2
  exit 1
fi
echo "  分析完成: $ANALYSIS_JSON"

echo ""
echo "═══════════════════════════════════════════"
echo "  Step 2/4: 直接生成 Prefect flow"
echo "═══════════════════════════════════════════"

PREFECT_SPIDER="${DEPLOY_REPO}/spiders/${SLUG}_spider.py"
PREFECT_PROMPT="使用当前目录的 \$scrapling-analysis-to-prefect-generator，根据 analysis_outputs/${SLUG}_analysis.json 里的分析结果，直接生成基于 Scrapling 的 Prefect flow，输出到 ${PREFECT_SPIDER}。只抓第一页。必须直接把代码写入这个文件路径；如果没有落盘到该文件就算失败。"
codex exec "${CODEX_ARGS[@]}" "$PREFECT_PROMPT"

if [[ ! -f "$PREFECT_SPIDER" ]]; then
  if [[ "$SANDBOX" != "danger-full-access" ]]; then
    echo "  首次生成未落盘，使用 danger-full-access 重试 ..."
    codex exec "${RETRY_CODEX_ARGS[@]}" "$PREFECT_PROMPT"
  fi
fi

if [[ ! -f "$PREFECT_SPIDER" ]]; then
  echo "错误: 未找到生成后的 Prefect 爬虫 $PREFECT_SPIDER；请优先检查 sandbox 设置" >&2
  exit 1
fi
echo "  Prefect 生成完成: $PREFECT_SPIDER"

echo ""
echo "═══════════════════════════════════════════"
echo "  Step 3/4: 注册并提交到 Prefect 仓库"
echo "═══════════════════════════════════════════"

DEPLOY_REGISTRY="${DEPLOY_REPO}/spiders/registry.yaml"
FLOW_FUNC=$(grep -oP '^def \K\w+_flow' "$PREFECT_SPIDER" | head -1)
if [[ -z "$FLOW_FUNC" ]]; then
  echo "警告: 未能从 $PREFECT_SPIDER 提取 flow 函数名，跳过 registry 注册" >&2
else
  ENTRY="spiders/${SLUG}_spider.py:${FLOW_FUNC}"
  FLOW_NAME=$(echo "$FLOW_FUNC" | tr '_' '-')
  insert_registry_entry "$DEPLOY_REGISTRY" "$ENTRY" "$FLOW_NAME" "$SLUG"
fi

if git -C "$DEPLOY_REPO" ls-files --error-unmatch "spiders/${SLUG}_spider.py" >/dev/null 2>&1; then
  COMMIT_MSG="fix: update spider ${SLUG}"
else
  COMMIT_MSG="feat: add spider ${SLUG}"
fi

git -C "$DEPLOY_REPO" add "spiders/${SLUG}_spider.py" "spiders/registry.yaml"
if git -C "$DEPLOY_REPO" diff --cached --quiet; then
  echo "  目标仓库无变化，跳过 commit"
else
  git -C "$DEPLOY_REPO" commit -m "$COMMIT_MSG"
  echo "  已提交到 $DEPLOY_REPO（未 push，请手动 git push）"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Step 4/4: 运行 Prefect spider (optional)"
echo "═══════════════════════════════════════════"

if [[ "$NO_RUN" = false ]]; then
  (
    cd "$DEPLOY_REPO"
    "$SCRIPT_DIR/.venv/bin/python" "spiders/${SLUG}_spider.py"
  )
else
  echo "跳过 Prefect spider 执行 (--no-run)"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Pipeline 完成"
echo "  分析: $ANALYSIS_JSON"
echo "  Prefect: $PREFECT_SPIDER"
echo "  部署仓库: $DEPLOY_REPO"
echo ""
echo "  ⚠ 请手动 push: git -C $DEPLOY_REPO push"
echo "═══════════════════════════════════════════"
