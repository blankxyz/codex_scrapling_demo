#!/usr/bin/env bash
set -euo pipefail

# ── 爬虫全自动 Pipeline ──
# 分析列表页 → 生成 Scrapling 爬虫 → 转换 Prefect flow → 部署到目标仓库
#
# 用法:
#   ./run_pipeline.sh <list-url> [选项]
#
# 示例:
#   # 新增爬虫（自动从 URL 生成标识）
#   ./run_pipeline.sh https://www.nxnews.net/sh/jjcz/
#
#   # 网站 URL 变了，覆盖已有爬虫（手动指定旧标识）
#   ./run_pipeline.sh https://www.nxnews.net/new-path/jjcz/ --slug www-nxnews-net-sh-jjcz
#
#   # 只生成不运行
#   ./run_pipeline.sh https://example.com/news/ --no-run

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 默认值 ──
MODEL=""
ANALYSIS_SANDBOX="danger-full-access"
SANDBOX="danger-full-access"
NO_RUN=false
HEADLESS=true
URL=""
SLUG_OVERRIDE=""
DEPLOY_REPO="/home/blank/playground/prefect_demo"

# ── 参数解析 ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)   MODEL="$2"; shift 2 ;;
    --sandbox) SANDBOX="$2"; ANALYSIS_SANDBOX="$2"; shift 2 ;;
    --analysis-sandbox) ANALYSIS_SANDBOX="$2"; shift 2 ;;
    --slug)    SLUG_OVERRIDE="$2"; shift 2 ;;
    --no-run)  NO_RUN=true; shift ;;
    --no-headless) HEADLESS=false; shift ;;
    -h|--help)
      cat <<'HELP'
用法: run_pipeline.sh <list-url> [选项]

爬虫全自动 Pipeline：分析 → 生成 → Prefect 转换 → 部署

参数:
  <list-url>              要分析的列表页 URL

选项:
  --slug <slug>           手动指定爬虫标识，覆盖自动生成的值
                          用于：网站 URL 变更但需要更新同一个爬虫
  --model <model>         Codex 使用的模型 (默认: codex 配置默认值)
  --sandbox <mode>        全流程统一 Sandbox 模式
                          默认不设置；若传入则分析/生成/转换都使用该值
  --analysis-sandbox <mode>
                          Step 1 分析专用 Sandbox 模式 (默认: danger-full-access)
  --no-run                跳过最后的爬虫执行步骤
  --no-headless           Chrome 使用有头模式（默认无头）
  -h, --help              显示此帮助信息

流程:
  Step 1  分析列表页结构，输出 analysis_outputs/<slug>_analysis.json
  Step 2  生成 Scrapling 爬虫，输出 spiders/<slug>_spider.py
  Step 3  转换为 Prefect flow，直接输出到目标仓库 spiders/<slug>_spider.py
  Step 4  在目标仓库 /home/blank/playground/prefect_demo/ 中注册并提交
          - 注册到 registry.yaml（新爬虫自动注册，已有跳过）
          - git commit（新增用 feat:，修复用 fix:，需手动 push）

示例:
  # 新增爬虫
  ./run_pipeline.sh https://www.nxnews.net/sh/jjcz/

  # 网站 URL 变了，覆盖已有爬虫
  ./run_pipeline.sh https://www.nxnews.net/new-path/ --slug www-nxnews-net-sh-jjcz

  # 只生成不运行
  ./run_pipeline.sh https://example.com/news/ --no-run

  # 强制整个流程都走 workspace-write
  ./run_pipeline.sh https://example.com/news/ --sandbox workspace-write
HELP
      exit 0
      ;;
    *)
      if [[ -z "$URL" ]]; then
        URL="$1"; shift
      else
        echo "错误: 未知参数 '$1'" >&2; exit 1
      fi
      ;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "错误: 请提供列表页 URL" >&2
  echo "用法: $0 <list-url> [--slug <slug>] [--model <model>] [--sandbox <mode>] [--analysis-sandbox <mode>] [--no-run]" >&2
  echo "运行 $0 --help 查看详细帮助" >&2
  exit 1
fi

# ── slug 生成 ──
# 从 URL 提取 host+path，转为 kebab-case
slug_from_url() {
  local url="$1"
  # 去掉协议
  local hostpath="${url#*://}"
  # 去掉查询串和锚点
  hostpath="${hostpath%%\?*}"
  hostpath="${hostpath%%#*}"
  # 去掉尾部斜线
  hostpath="${hostpath%/}"
  # 替换 /._: 为 -
  local slug
  slug=$(echo "$hostpath" | tr '/._:' '-' | tr -s '-' | sed 's/^-//;s/-$//')
  # 截断到 60 字符
  echo "${slug:0:60}"
}

if [[ -n "$SLUG_OVERRIDE" ]]; then
  SLUG="$SLUG_OVERRIDE"
else
  SLUG=$(slug_from_url "$URL")
fi
echo "═══════════════════════════════════════════"
echo "  Pipeline: $URL"
echo "  Slug:     $SLUG"
echo "  Analysis sandbox: $ANALYSIS_SANDBOX"
echo "  Other steps:      $SANDBOX"
echo "═══════════════════════════════════════════"

# ── 构建 codex exec 公共参数 ──
ANALYSIS_CODEX_ARGS=(-s "$ANALYSIS_SANDBOX")
CODEX_ARGS=(-s "$SANDBOX")
RETRY_CODEX_ARGS=(-s danger-full-access)
if [[ -n "$MODEL" ]]; then
  ANALYSIS_CODEX_ARGS+=(-m "$MODEL")
  CODEX_ARGS+=(-m "$MODEL")
  RETRY_CODEX_ARGS+=(-m "$MODEL")
fi

# ── Chrome CDP 启动 ──
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
    echo " OK"; break
  fi
  echo -n "."; sleep 1
done

if ! curl -sf "${CDP_URL}/json/version" >/dev/null 2>&1; then
  echo ""
  echo "错误: Chrome CDP 启动超时，请检查 Chrome 安装" >&2
  kill "$CDP_PID" 2>/dev/null || true
  exit 1
fi
echo "  CDP 就绪 (PID: $CDP_PID)"

# ── Step 1: Analysis ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Step 1/4: 分析列表页"
echo "═══════════════════════════════════════════"

ANALYSIS_PROMPT="使用当前目录的 \$scrapling-spider-analysis 分析这个列表页，并把结果输出到 analysis_outputs/${SLUG}_analysis.json：${URL}"

codex exec "${ANALYSIS_CODEX_ARGS[@]}" "$ANALYSIS_PROMPT"

# 检查 analysis 输出（严格匹配，不回退）
ANALYSIS_JSON="analysis_outputs/${SLUG}_analysis.json"
if [[ ! -f "$ANALYSIS_JSON" ]]; then
  echo "错误: 未找到本次分析结果 $ANALYSIS_JSON" >&2
  exit 1
fi
echo "  分析完成: $ANALYSIS_JSON"

# ── Step 2: Generation ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Step 2/4: 生成爬虫代码"
echo "═══════════════════════════════════════════"

# 期望的爬虫文件名与 slug 对应
NEW_SPIDER="spiders/${SLUG}_spider.py"

GEN_PROMPT="使用当前目录的 \$scrapling-spider-generator，根据 analysis_outputs/${SLUG}_analysis.json 里的分析结果生成 Scrapling 爬虫，输出到 ${NEW_SPIDER}。只抓第一页。必须直接把代码写入这个文件路径；如果没有落盘到该文件就算失败。"

codex exec "${CODEX_ARGS[@]}" "$GEN_PROMPT"

# 严格检查本次生成的爬虫文件；若非 danger-full-access 且未落盘，则自动重试一次
if [[ ! -f "$NEW_SPIDER" ]]; then
  if [[ "$SANDBOX" != "danger-full-access" ]]; then
    echo "  首次生成未落盘，使用 danger-full-access 重试 ..."
    codex exec "${RETRY_CODEX_ARGS[@]}" "$GEN_PROMPT"
  fi
fi

if [[ ! -f "$NEW_SPIDER" ]]; then
  echo "错误: 未找到本次生成的爬虫 $NEW_SPIDER；请优先检查 sandbox 设置" >&2
  exit 1
fi

echo "  爬虫生成完成: $NEW_SPIDER"

# ── Step 3: Prefect 转换 ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Step 3/4: 转换为 Prefect flow"
echo "═══════════════════════════════════════════"

PREFECT_SPIDER="${DEPLOY_REPO}/spiders/${SLUG}_spider.py"

PREFECT_PROMPT="使用当前目录的 \$scrapling-to-prefect-generator，将 ${NEW_SPIDER} 转换为 Prefect flow，输出到 ${PREFECT_SPIDER}。必须直接把代码写入这个文件路径；如果没有落盘到该文件就算失败。"

codex exec "${CODEX_ARGS[@]}" "$PREFECT_PROMPT"

if [[ ! -f "$PREFECT_SPIDER" ]]; then
  if [[ "$SANDBOX" != "danger-full-access" ]]; then
    echo "  首次 Prefect 转换未落盘，使用 danger-full-access 重试 ..."
    codex exec "${RETRY_CODEX_ARGS[@]}" "$PREFECT_PROMPT"
  fi
fi

if [[ ! -f "$PREFECT_SPIDER" ]]; then
  echo "错误: 未找到转换后的 Prefect 爬虫 $PREFECT_SPIDER；请优先检查 sandbox 设置" >&2
  exit 1
fi

echo "  Prefect 转换完成: $PREFECT_SPIDER"

# ── Step 4: 部署到目标仓库 ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Step 4/4: 注册并提交到 Prefect 仓库"
echo "═══════════════════════════════════════════"

DEPLOY_SPIDERS_DIR="${DEPLOY_REPO}/spiders"
DEPLOY_REGISTRY="${DEPLOY_SPIDERS_DIR}/registry.yaml"

# 4a: 从文件中提取 flow 函数名
FLOW_FUNC=$(grep -oP '^def \K\w+_flow' "$PREFECT_SPIDER" | head -1)
if [[ -z "$FLOW_FUNC" ]]; then
  echo "警告: 未能从 $PREFECT_SPIDER 提取 flow 函数名，跳过 registry 注册" >&2
else
  ENTRY="spiders/${SLUG}_spider.py:${FLOW_FUNC}"
  # 4b: 检查 registry 是否已有该条目
  if grep -qF "$ENTRY" "$DEPLOY_REGISTRY"; then
    echo "  registry.yaml 已包含 $ENTRY，跳过"
  else
    # 在 spiders: 段末尾（platform: 之前）插入新条目
    FLOW_NAME=$(echo "$FLOW_FUNC" | tr '_' '-')
    cat >> /tmp/_registry_entry.yaml <<EOF

  - entrypoint: ${ENTRY}
    name: ${FLOW_NAME}
    interval: 86400
    description: ${SLUG} 自动生成爬虫
    tags: [auto-generated]
EOF
    # 插入到 platform: 行之前
    sed -i "/^# 平台工具/r /tmp/_registry_entry.yaml" "$DEPLOY_REGISTRY"
    rm -f /tmp/_registry_entry.yaml
    echo "  已注册到 registry.yaml: $ENTRY"
  fi

  # 4c: 判断新增还是修复（在 git add 之前检查）
  if git -C "$DEPLOY_REPO" ls-files --error-unmatch "spiders/${SLUG}_spider.py" >/dev/null 2>&1; then
    COMMIT_PREFIX="fix"
    COMMIT_MSG="fix: update spider ${SLUG}"
  else
    COMMIT_PREFIX="feat"
    COMMIT_MSG="feat: add spider ${SLUG}"
  fi

  git -C "$DEPLOY_REPO" add "spiders/${SLUG}_spider.py" "spiders/registry.yaml"
  if git -C "$DEPLOY_REPO" diff --cached --quiet; then
    echo "  目标仓库无变化，跳过 commit"
  else
    git -C "$DEPLOY_REPO" commit -m "$COMMIT_MSG"
    echo "  已提交到 $DEPLOY_REPO（未 push，请手动 git push）"
  fi
fi

# ── Step 5: Run (optional) ──
if [[ "$NO_RUN" = false ]]; then
  echo ""
  echo "═══════════════════════════════════════════"
  echo "  运行爬虫: $NEW_SPIDER"
  echo "═══════════════════════════════════════════"
  .venv/bin/python "$NEW_SPIDER"
else
  echo ""
  echo "跳过爬虫执行 (--no-run)"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Pipeline 完成"
echo "  分析: $ANALYSIS_JSON"
echo "  爬虫: $NEW_SPIDER"
echo "  Prefect: $PREFECT_SPIDER"
echo "  部署仓库: $DEPLOY_REPO"
echo ""
echo "  ⚠ 请手动 push: git -C $DEPLOY_REPO push"
echo "═══════════════════════════════════════════"
