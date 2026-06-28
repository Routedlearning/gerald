#!/usr/bin/env bash
set -euo pipefail

SOURCE="/root/projects/fitness-coach/workout_history.json"
BACKUP_DIR="/root/projects/fitness-coach/backups"
LOG_DIR="/root/projects/fitness-coach/logs"
LOG_FILE="$LOG_DIR/backup.log"
MAX_BACKUPS=30

mkdir -p "$BACKUP_DIR" "$LOG_DIR"

if [ ! -f "$SOURCE" ]; then
  echo "[$(date -Iseconds)] ERROR: Source file not found: $SOURCE" >> "$LOG_FILE"
  exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEST="$BACKUP_DIR/workout_history_$TIMESTAMP.json"

cp "$SOURCE" "$DEST"
chmod 0600 "$DEST"

# Rotate old backups
ls -1t "$BACKUP_DIR"/workout_history_*.json 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -f

echo "[$(date -Iseconds)] OK: Backup created at $DEST ($(wc -c < "$DEST") bytes)" >> "$LOG_FILE"
exit 0
