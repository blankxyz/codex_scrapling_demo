#!/usr/bin/env bash
set -euo pipefail

PORT="${CHROME_CDP_PORT:-9222}"
USER_DATA_DIR="${CHROME_CDP_USER_DATA_DIR:-/tmp/chrome-cdp-profile}"
CHROME_BIN="${CHROME_BIN:-}"
START_URL="${1:-about:blank}"

if [[ -z "$CHROME_BIN" ]]; then
  for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then
      CHROME_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$CHROME_BIN" ]]; then
  echo "No Chrome/Chromium binary found. Set CHROME_BIN=/path/to/chrome." >&2
  exit 1
fi

mkdir -p "$USER_DATA_DIR"

echo "Starting Chrome CDP"
echo "  binary:        $CHROME_BIN"
echo "  port:          $PORT"
echo "  user data dir: $USER_DATA_DIR"
echo "  start url:     $START_URL"
echo
echo "CDP endpoints:"
echo "  http://127.0.0.1:${PORT}/json/version"
echo "  http://127.0.0.1:${PORT}/json"
echo

HEADLESS="${CHROME_HEADLESS:-false}"

HEADLESS_FLAGS=()
if [[ "$HEADLESS" == "true" ]]; then
  HEADLESS_FLAGS=(--headless=new)
  echo "  headless:      on"
else
  echo "  headless:      off"
fi

WSL2_FLAGS=()
if uname -r | grep -qi microsoft; then
  echo "  environment:   WSL2 (--no-sandbox etc.)"
  WSL2_FLAGS=(--no-sandbox --disable-dev-shm-usage --disable-software-rasterizer)
fi

exec "$CHROME_BIN" \
  "${HEADLESS_FLAGS[@]}" \
  "${WSL2_FLAGS[@]}" \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$USER_DATA_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-gpu \
  "$START_URL"
