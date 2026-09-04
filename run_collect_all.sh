#!/usr/bin/env bash
# 88カ国ぶんの収集を最後まで回す。
# collect_country.py は1回の実行で全対象国を回るが、
# 途中で落ちても shortfall() が残りを数え直すので続きから再開できる。
# 相対パスだと実行元によってずれるので絶対パスで固定する。
cd /c/Users/shun/OneDrive/work/geoguessr-flora || exit 1
LOG=data/collect_country.log
for i in $(seq 1 60); do
  echo "=== 周回 $i ===" >> "$LOG"
  python src/collect_country.py >> "$LOG" 2>&1
  if python -c "
import sys; sys.path.insert(0,'src')
from collect_country import shortfall
sys.exit(1 if shortfall() else 0)
"; then
    echo '全カ国が目標に到達' >> "$LOG"; break
  fi
done
