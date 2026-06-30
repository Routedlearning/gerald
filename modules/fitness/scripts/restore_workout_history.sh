#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$BASE_DIR"

BACKUP_DIR="$PROJECT_DIR/backups"
HISTORY_FILE="$PROJECT_DIR/workout_history.json"
STORAGE_PY="$PROJECT_DIR/storage.py"
MAX_BACKUPS=30

die() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "$*"; }

ensure_dirs() {
  mkdir -p "$BACKUP_DIR"
  mkdir -p "$(dirname "$HISTORY_FILE")"
}

list_backups() {
  ensure_dirs
  ls -1t "$BACKUP_DIR"/workout_history_*.json 2>/dev/null || true
}

validate_backup() {
  local backup_path="$1"
  python3 "$STORAGE_PY" "$backup_path" <<'PY'
import sys, json
from storage import validate

backup_path = sys.argv[1]

with open(backup_path, "r") as f:
    state = json.load(f)

try:
    validate(state)
    print(f"VALID: {backup_path}")
except Exception as e:
    print(f"INVALID: {backup_path} — {e}")
    sys.exit(2)
PY
}

pre_restore_backup() {
  local ts
  ts=$(date +%Y%m%d_%H%M%S)
  local dest="$BACKUP_DIR/workout_history_prerestore_${ts}.json"
  cp "$HISTORY_FILE" "$dest"
  chmod 0600 "$dest"
  info "Pre-restore backup saved to $dest"
}

rotate_backups() {
  local dir="$1"
  local max="${2:-30}"
  if [ ! -d "$dir" ]; then
    return
  fi
  ls -1t "$dir"/workout_history_*.json 2>/dev/null | tail -n +$((max + 1)) | xargs -r rm -f
  # also keep prerestore and quarantine under rotation if desired
  ls -1t "$dir"/workout_history_prerestore_*.json 2>/dev/null | tail -n +$((max + 1)) | xargs -r rm -f
}

do_restore() {
  local backup_path="$1"
  [ -f "$backup_path" ] || die "Backup file not found: $backup_path"

  # Validate backup contents
  info "Validating backup..."
  validation_output=$(validate_backup "$backup_path") || {
    echo "$validation_output" >&2
    exit 1
  }
  info "$validation_output"

  # Pre-restore backup of current live file
  if [ -f "$HISTORY_FILE" ]; then
    pre_restore_backup
  fi

  ensure_dirs

  # Atomic restore via temp file in same directory
  local dir_name
  dir_name=$(dirname "$HISTORY_FILE")
  local tmp_path
  tmp_path=$(mktemp "$dir_name/$(basename "$HISTORY_FILE").restore.XXXXXX")
  cp "$backup_path" "$tmp_path"
  chmod 0600 "$tmp_path"
  mv -f "$tmp_path" "$HISTORY_FILE"
  chmod 0600 "$HISTORY_FILE"

  info "Restored $backup_path -> $HISTORY_FILE"

  rotate_backups "$BACKUP_DIR" "$MAX_BACKUPS"
}

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--list | --latest | <filename>]

Options:
  --list            List available backups
  --latest          Restore the most recent backup
  <filename>        Restore a specific backup by filename

Examples:
  $(basename "$0") --list
  $(basename "$0") --latest
  $(basename "$0") workout_history_20260628_202551.json
USAGE
}

# Main
case "${1:-}" in
  --list)
    list_backups
    ;;
  --latest)
    latest=$(list_backups | head -n 1)
    [ -n "$latest" ] || die "No backups found"
    do_restore "$latest"
    ;;
  "")
    usage
    exit 1
    ;;
  *)
    do_restore "$1"
    ;;
esac
