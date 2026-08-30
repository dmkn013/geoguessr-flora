# -*- coding: utf-8 -*-
"""収集と判定の進み具合を1画面で出す。

    python src/status.py

長時間回すので、ログを追わなくても
「どの種があと何枚か」「判定待ちが何枚あるか」が分かるようにする。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from species import SPECIES  # noqa: E402
from verify_points import CAND, TARGET_PER_SPECIES, VERIFIED, load_state  # noqa: E402


def main():
    rows = []
    t_acc = t_rej = t_pend = t_noimg = 0
    for s in SPECIES:
        sid = s["id"]
        st = load_state(sid) if (VERIFIED / f"{sid}.json").exists() else None
        p = CAND / sid / "_pending.json"
        pend = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        acc = len(st["accepted"]) if st else 0
        rej = len(st["rejected"]) if st else 0
        noi = len(st["no_imagery"]) if st else 0
        rows.append((sid, s["ja"], acc, rej, len(pend), noi))
        t_acc += acc
        t_rej += rej
        t_pend += len(pend)
        t_noimg += noi

    print(f"{'種':16s}{'和名':12s} 採用 却下 判定待 写真無  収集")
    for sid, ja, acc, rej, pend, noi in rows:
        have = acc + rej + pend
        bar = "█" * int(min(have, TARGET_PER_SPECIES) / TARGET_PER_SPECIES * 12)
        print(f"{sid:16s}{ja:12s}{acc:4d}{rej:5d}{pend:6d}{noi:7d}  "
              f"{have:2d}/{TARGET_PER_SPECIES} {bar}")

    n_done = sum(1 for r in rows if r[2] + r[3] + r[4] >= TARGET_PER_SPECIES)
    print(f"\n収集: {n_done}/{len(rows)} 種が目標到達 "
          f"（写真の無かった地点 {t_noimg:,} 点）")
    print(f"判定: 採用 {t_acc} / 却下 {t_rej} / **判定待ち {t_pend} 枚**")
    if t_pend:
        print("\n  python src/review_ui.py   → dist/review.html をブラウザで開く")


if __name__ == "__main__":
    main()
