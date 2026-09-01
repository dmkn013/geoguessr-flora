#!/usr/bin/env bash
# ランダム収集を落ちても再開しながら回す。10,000枚は数日かかる。
cd "$(dirname "$0")/.." || exit 1
LOG=data/random.log
while true; do
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 開始 =====" >> "$LOG"
  PYTHONIOENCODING=utf-8 python -u src/collect_random.py >> "$LOG" 2>&1
  code=$?
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 終了 code=$code =====" >> "$LOG"
  [ $code -eq 0 ] || [ $code -eq 1 ] && break
  sleep 30
done
