#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/cron_dispatch.log"
CLI_DIR="$BASE_DIR"
CLI_SCRIPT="$CLI_DIR/cli.py"
WEEK_START="${1:-2026-06-29}"

mkdir -p "$LOG_DIR"

cd "$CLI_DIR" || { echo "ERROR: cannot cd to $CLI_DIR"; echo "$(date -Iseconds) ERROR: cd failed" >> "$LOG_FILE"; exit 1; }

OUTPUT=$(python3 "$CLI_SCRIPT" --week-start "$WEEK_START" --today 2>&1)
EXIT_CODE=$?

{
  echo "=== $(date -Iseconds) ==="
  echo "Week start: $WEEK_START"
  echo "Exit code: $EXIT_CODE"
  echo "--- OUTPUT START ---"
  echo "$OUTPUT"
  echo "--- OUTPUT END ---"
} >> "$LOG_FILE"

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$OUTPUT"
else
  LAST_ERROR=$(printf '%s\n' "$OUTPUT" | tail -n 1)
  echo "FALLBACK: Fitness engine failed. Last error: $LAST_ERROR"
fi
