# -*- coding: utf-8 -*-
"""サブエージェント判定用のシートを作る。

判定はコンテキストに画像を読み込む必要があるので、
Opus（このセッション）ではなく Sonnet のサブエージェントに任せる。
サブエージェントは画像を見て採否を返し、こちらは結果を記録するだけ。

    python src/judge_agent.py sheet <種id> <ページ>   # シート作成
    python src/judge_agent.py apply <種id> ok 0 3 5   # 結果反映
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from full_sheet import build  # noqa: E402
from judge_sheet import decide  # noqa: E402
from species import SPECIES  # noqa: E402

BYID = {s["id"]: s for s in SPECIES}

if __name__ == "__main__":
    cmd = sys.argv[1]
    sid = sys.argv[2]
    if cmd == "sheet":
        page = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        out, n, total = build(sid, page)
        if not n:
            print(f"{sid}: 未判定なし")
            sys.exit()
        s = BYID[sid]
        print(f"PATH={out}")
        print(f"N={n}")
        print(f"種={s['ja']}（{s['sci']}）")
        print(f"採用条件={' / '.join(s['tells'])}")
    elif cmd == "apply":
        ok = sys.argv[3] == "ok"
        decide(sid, sys.argv[4:], ok)
