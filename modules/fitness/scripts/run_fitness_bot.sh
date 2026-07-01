#!/usr/bin/env bash
set -euo pipefail
cd "/root/projects/gerald/modules/fitness" || { echo "cd failed"; exit 1; }
if [ ! -f .env ]; then
  echo ".env missing" >&2
  exit 1
fi
set -a
source .env
set +a
exec python3 telegram_fitness_bot.py