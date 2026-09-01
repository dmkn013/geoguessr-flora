# -*- coding: utf-8 -*-
"""1種を最後まで判定するためのコマンド。サブエージェントが使う。

    python src/judge_one.py next <種id>          # 次のシートを出す
    python src/judge_one.py ok   <種id> 0 3 5    # 採用
    python src/judge_one.py ng   <種id> 1 2 4    # 却下

next が「完了」を返すまで繰り返す。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from full_sheet import build  # noqa: E402
from judge_sheet import decide  # noqa: E402
from species import SPECIES  # noqa: E402

BYID = {s["id"]: s for s in SPECIES}

cmd, sid = sys.argv[1], sys.argv[2]
if cmd == "next":
    out, n, total = build(sid, 1)
    if not n:
        print("完了: この種はすべて判定済み")
    else:
        s = BYID[sid]
        print(f"画像パス: {out}")
        print(f"枚数: {n}（残り{total}枚）")
        print(f"種: {s['ja']}（{s['sci']}）")
        print(f"採用条件: {' / '.join(s['tells'])}")
elif cmd in ("ok", "ng"):
    decide(sid, sys.argv[3:], cmd == "ok")
