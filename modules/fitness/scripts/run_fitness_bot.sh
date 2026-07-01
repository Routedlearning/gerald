#!/usr/bin/env bash
set -euo pipefail
cd "/root/projects/gerald/modules/fitness" || { echo "cd failed"; exit 1; }
exec python3 telegram_fitness_bot.py