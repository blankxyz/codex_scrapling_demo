#!/usr/bin/env bash
set -euo pipefail

# ── 串联 scrapling-spider-analysis + scrapling-spider-generator ──
# 用法: ./run_pipeline.sh <list-url> [--model <model>] [--sandbox <mode>] [--no-run]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 默认值 ──
MODEL=""
SANDBOX="workspace-write"
NO_RUN=false
URL=""

# ── 参数解析 ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)   MODEL="$2"; shift 2 ;;
    --sandbox) SANDBOX="$2"; shift 2 ;;
    --no-run)  NO_RUN=true; shift ;;
    -h|--help)
      echo "用法: $0 <list-url> [--model <model>] [--sandbox <mode>] [--no-run]"
      echo ""
      echo "  <list-url>       要分析的列表页 URL"
      echo "  --model <model>  Codex 使用的模型 (默认: codex 配置默认值)"
      echo "  --sandbox <mode> Sandbox 模式 (默认: workspace-write)"
      echo "  --no-run         跳过最后的爬虫执行步骤"
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
  echo "用法: $0 <list-url> [--model <model>] [--sandbox <mode>] [--no-run]" >&2
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

SLUG=$(slug_from_url "$URL")
echo "═══════════════════════════════════════════"
echo "  Pipeline: $URL"
echo "  Slug:     $SLUG"
echo "═══════════════════════════════════════════"

# ── 构建 codex exec 公共参数 ──
CODEX_ARGS=(-s "$SANDBOX")
if [[ -n "$MODEL" ]]; then
  CODEX_ARGS+=(-m "$MODEL")
fi

# ── CDP 重启 ──
CDP_URL="${CHROME_CDP_URL:-http://127.0.0.1:9222}"
CDP_PORT="${CHROME_CDP_PORT:-9222}"
echo ""
echo "▶ 关闭已有的 Chrome CDP 进程 ..."
if lsof -ti :"$CDP_PORT" >/dev/null 2>&1; then
  lsof -ti :"$CDP_PORT" | xargs kill 2>/dev/null || true
  sleep 1
fi

echo "▶ 启动新的 Chrome CDP ..."
"$SCRIPT_DIR/start_chrome_cdp.sh" &
CDP_PID=$!

# 轮询等待 CDP 就绪（最多 15 秒）
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

# ── Step 1: Analysis ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Step 1/2: 分析列表页"
echo "═══════════════════════════════════════════"

ANALYSIS_PROMPT="使用当前目录的 \$scrapling-spider-analysis 分析这个列表页，并把结果输出到 analysis_outputs/${SLUG}_analysis.json：${URL}"

codex exec "${CODEX_ARGS[@]}" "$ANALYSIS_PROMPT"

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
echo "  Step 2/2: 生成爬虫代码"
echo "═══════════════════════════════════════════"

# 期望的爬虫文件名与 slug 对应
NEW_SPIDER="spiders/${SLUG}_spider.py"

GEN_PROMPT="使用当前目录的 \$scrapling-spider-generator，根据 analysis_outputs/${SLUG}_analysis.json 里的分析结果生成 Scrapling 爬虫，输出到 ${NEW_SPIDER}。只抓第一页。"

codex exec "${CODEX_ARGS[@]}" "$GEN_PROMPT"

# 严格检查本次生成的爬虫文件
if [[ ! -f "$NEW_SPIDER" ]]; then
  echo "错误: 未找到本次生成的爬虫 $NEW_SPIDER" >&2
  exit 1
fi

echo "  爬虫生成完成: $NEW_SPIDER"

# ── Step 3: Run (optional) ──
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
echo "═══════════════════════════════════════════"
