#!/usr/bin/env bash
# 収集を落ちても再開しながら回し続ける。
#
# 長時間（数日〜1週間）回す前提なので、
# 回線断・API側の一時障害・OS再起動などで落ちても勝手に戻ってくるようにする。
# 状態は data/verified/*.json と data/candidates/*/_pending.json に
# 都度書かれているので、再開しても取り直しにはならない。
#
#   bash src/run_collect.sh            # 全種
#   bash src/run_collect.sh saguaro    # 種を指定
cd "$(dirname "$0")/.." || exit 1
LOG=data/collect.log

while true; do
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 開始 =====" >> "$LOG"
  PYTHONIOENCODING=utf-8 python -u src/verify_points.py "$@" >> "$LOG" 2>&1
  code=$?
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 終了 code=$code =====" >> "$LOG"
  # 0 = 収集完了、1 = トークン不正。どちらも再開しない
  if [ $code -eq 0 ] || [ $code -eq 1 ]; then
    break
  fi
  sleep 30
done
