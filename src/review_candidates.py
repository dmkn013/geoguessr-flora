# -*- coding: utf-8 -*-
"""候補写真をコンタクトシートにして、採否を決める。

    python src/review_candidates.py sheet eucalyptus     # シートを作る
    python src/review_candidates.py accept eucalyptus 0 2 5   # 0,2,5番を採用
    python src/review_candidates.py reject eucalyptus 1 3 4   # それ以外を却下

判定は「**その植物が画面に写っているか**」だけ。
写っていなければ捨てる。分布域の中でも実際に写っていなければ点は残さない。
それがこの方式の要点で、点1つ1つが写真で裏付けられた状態になる。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA, DIST  # noqa: E402
from review_photos import F_NAME, F_SUB  # noqa: E402
from species import SPECIES  # noqa: E402
from verify_points import CAND, load_state, save_state  # noqa: E402

BYID = {s["id"]: s for s in SPECIES}
CELL = 400


def pending(sid):
    p = CAND / sid / "_pending.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def sheet(sid):
    items = pending(sid)
    if not items:
        print(f"{sid}: 候補が無い。先に verify_points.py を回す"); return
    s = BYID[sid]
    cells = []
    for i, it in enumerate(items):
        f = CAND / sid / it["file"]
        im = Image.open(f).convert("RGB")
        im.thumbnail((CELL, CELL), Image.LANCZOS)
        cv = Image.new("RGB", (CELL, CELL + 46), (250, 249, 246))
        cv.paste(im, ((CELL - im.width) // 2, 0))
        d = ImageDraw.Draw(cv)
        d.text((6, CELL + 4), f"[{i}] {it['lat']:.3f}, {it['lon']:.3f}",
               font=F_NAME, fill=(20, 20, 20))
        d.text((6, CELL + 25), f"要: {s['tells'][0][:44]}", font=F_SUB, fill=(90, 90, 90))
        cells.append(cv)
    cols = min(3, len(cells))
    rows = (len(cells) + cols - 1) // cols
    W, H = cells[0].size
    sh = Image.new("RGB", (cols * W, rows * H), (255, 255, 255))
    for i, c in enumerate(cells):
        sh.paste(c, ((i % cols) * W, (i // cols) * H))
    out = DIST / f"candidates_{sid}.png"
    sh.save(out)
    print(f"保存: {out}  ({len(items)}件)")
    print(f"  {s['ja']} / 見るべき特徴: {s['tells'][0]}")


def decide(sid, idxs, accept):
    items = pending(sid)
    st = load_state(sid)
    for i in idxs:
        if i >= len(items):
            print(f"  [{i}] 範囲外"); continue
        it = items[i]
        (st["accepted"] if accept else st["rejected"]).append(it)
    save_state(sid, st)
    print(f"{sid}: 採用 {len(st['accepted'])} / 却下 {len(st['rejected'])}"
          f" / 写真なし {len(st['no_imagery'])}")


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    cmd, sid = sys.argv[1], sys.argv[2]
    if cmd == "sheet":
        sheet(sid)
    elif cmd in ("accept", "reject"):
        decide(sid, [int(x) for x in sys.argv[3:]], cmd == "accept")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
