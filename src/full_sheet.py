# -*- coding: utf-8 -*-
"""未判定を3x3のシートに切って出す。

    python src/full_sheet.py <種id> [ページ番号]

**1枚を大きく出すこと**が要件。8x5に詰めたら樹冠の形が潰れて
見落としが出た（ユーザー指摘）。判定の精度が落ちては本末転倒なので、
往復が増えても3x3を維持する。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DIST  # noqa: E402
from review_photos import F_NAME, F_SUB  # noqa: E402
from species import SPECIES  # noqa: E402
from verify_points import load_state  # noqa: E402

BYID = {s["id"]: s for s in SPECIES}
C = 620
COLS = 3
PER = 9


def build(sid, page=1):
    p = CANDIDATES / sid / "_pending.json"
    if not p.exists():
        return None, 0
    items = json.loads(p.read_text(encoding="utf-8"))
    st = load_state(sid)
    done = {i["img_id"] for i in st["accepted"]} | {i["img_id"] for i in st["rejected"]}
    items = [i for i in items if i["img_id"] not in done]
    if not items:
        return None, 0, 0
    total = len(items)
    items = items[(page - 1) * PER:(page - 1) * PER + PER]
    if not items:
        return None, 0, total
    cells = []
    for i, it in enumerate(items):
        im = Image.open(CANDIDATES / sid / it["file"]).convert("RGB")
        if im.width / im.height > 1.9:      # 全天球は中央だけ使う
            w = int(im.height * 1.6)
            im = im.crop(((im.width - w) // 2, 0, (im.width + w) // 2, im.height))
        im.thumbnail((C, C), Image.LANCZOS)
        cv = Image.new("RGB", (C, C + 16), (250, 249, 246))
        cv.paste(im, ((C - im.width) // 2, (C - im.height) // 2))
        d = ImageDraw.Draw(cv)
        d.rectangle([2, 2, 34, 24], fill=(20, 20, 20))
        d.text((9, 4), str(i), font=F_NAME, fill=(255, 255, 255))
        d.text((40, 6), f"{it['lat']:.2f},{it['lon']:.2f}", font=F_SUB, fill=(90, 90, 90))
        cells.append(cv)
    rows = (len(cells) + COLS - 1) // COLS
    W, H = cells[0].size
    sh = Image.new("RGB", (COLS * W, rows * H), (255, 255, 255))
    for i, c in enumerate(cells):
        sh.paste(c, ((i % COLS) * W, (i // COLS) * H))
    out = DIST / f"full_{sid}.png"
    sh.save(out)
    (DIST / "_page.json").write_text(json.dumps(
        {"sid": sid, "page": 1, "ids": [i["img_id"] for i in items]},
        ensure_ascii=False), encoding="utf-8")
    return out, len(cells), total


if __name__ == "__main__":
    sid = sys.argv[1]
    page = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    out, n, total = build(sid, page)
    if not n:
        print(f"{sid}: 未判定なし")
        sys.exit()
    s = BYID[sid]
    print(f"{out}  ({n}枚 / 未判定 {total}枚)")
    print(f"■ {s['ja']}（{s['sci']}）")
    print(f"  採用条件: {' / '.join(s['tells'])}")
