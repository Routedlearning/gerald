#!/usr/bin/env bash
set -uo pipefail
cd "/root/projects/gerald/modules/fitness" || { echo "cd failed"; exit 1; }
: "${GERALD_ALLOWED_CHAT_ID:=7435551643}"
export GERALD_ALLOWED_CHAT_ID
exec python3 inbound_feedback.py
