# -*- coding: utf-8 -*-
"""採用された地点の車載写真を data URI にして data/verified_photos.json に出す。

図鑑写真（photos.json）とは役割が違う:
  - photos.json          種ごとに1枚。図鑑的な「この種はこう見える」
  - verified_photos.json **点ごと**。「この地点で実際にこう写っていた」

点ごとなので枚数が多い。Artifact の16MB制限に収めるため、
図鑑写真より小さく圧縮する（詳細パネルで見る用で、拡大はしない）。

CC BY-SA なので撮影者名を必ず一緒に持つ。
"""
import base64
import json
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402
from species import SPECIES  # noqa: E402
from verify_points import CAND, VERIFIED, load_state  # noqa: E402

OUT = DATA / "verified_photos.json"

# 点ごとに持つので図鑑写真より小さくする。
# 「そこに何が写っていたか」が分かればよく、細部の鑑賞用ではない。
MAX_W, MAX_H = 420, 300
QUALITY = 70
BUDGET_MB = 10.0        # 図鑑写真4MBと合わせて16MBに収める


def encode(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
    b = BytesIO()
    im.save(b, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    raw = b.getvalue()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"), len(raw)


def main():
    out, total, n = {}, 0, 0
    for s in SPECIES:
        sid = s["id"]
        if not (VERIFIED / f"{sid}.json").exists():
            continue
        st = load_state(sid)
        items = []
        for a in st["accepted"]:
            f = CAND / sid / a["file"]
            if not f.exists():
                continue
            uri, nbytes = encode(f)
            total += nbytes
            n += 1
            items.append({
                "lat": a["lat"], "lon": a["lon"], "src": uri,
                # CC BY-SA の帰属表示。撮影者とMapillaryの画像IDを残す
                "by": a.get("creator", ""),
                "img": a["img_id"],
            })
        if items:
            out[sid] = items
            print(f"{sid:16s} {len(items):3d}枚")

    b64 = total * 4 / 3 / 1048576
    print(f"\n{n}枚 / 元 {total/1048576:.2f} MB / base64換算 {b64:.2f} MB")
    if b64 > BUDGET_MB:
        print(f"!! 予算 {BUDGET_MB} MB 超過。MAX_W か QUALITY を下げること")
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("保存:", OUT)
    if not n:
        print("（まだ採用が0件。review_ui.py で判定する）")


if __name__ == "__main__":
    main()
