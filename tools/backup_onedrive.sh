#!/bin/zsh
# Automatic backup of the solar-olympiade project to OneDrive (runs every 15 min via launchd).
# Nothing is ever deleted in the backup: removed/renamed files stay in OneDrive.
SRC="$HOME/Downloads/solar-olympiade/"
DST="$HOME/Library/CloudStorage/OneDrive-Personal/claude/Projecten/solar-olympiade/"
LOG="$HOME/Library/Logs/solar-olympiade-backup.log"
mkdir -p "$DST"
/usr/bin/rsync -a --exclude '.venv' --exclude '__pycache__' --exclude 'cad/out/print/_*' \
  --exclude 'node_modules' --exclude '.DS_Store' "$SRC" "$DST" >> "$LOG" 2>&1 \
  && echo "$(date '+%F %T') backup ok" >> "$LOG" \
  || echo "$(date '+%F %T') backup FAILED ($?)" >> "$LOG"
