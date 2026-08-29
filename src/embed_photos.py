# -*- coding: utf-8 -*-
"""目視で採用した画像を縮小・JPEG化して data/photos.json（data URI）にする。

なぜ埋め込むか: Artifact は外部へ通信できないので、画像も本文に入れるしかない。
ローカルで開く場合も1枚のHTMLで完結するほうが扱いやすいので同じ方式にする。

サイズ設計: Artifact の上限が16MB。HTML本体が約0.26MBなので画像に使えるのは
実質15MB前後だが、base64は元バイトの約1.33倍に膨らむ点に注意する。
48種×1枚で1枚あたり平均90KBに収めれば base64込みで約5.8MB。余裕を見てこの線を狙う。
"""
import base64
import json
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from annotations import ANNOTATIONS  # noqa: E402
from paths import DATA  # noqa: E402
from species import SPECIES  # noqa: E402

RAW = DATA / "photos_raw"
OUT = DATA / "photos.json"

MAX_W, MAX_H = 640, 480
QUALITY = 78
BUDGET_MB = 15.0


def encode(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
    buf = BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    raw = buf.getvalue()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"), len(raw), im.size


def main():
    meta = json.loads((RAW / "_meta.json").read_text(encoding="utf-8"))
    # 目視で落としたものは reject.json に id を並べる（無ければ全採用）
    rej_path = RAW / "_reject.json"
    reject = set(json.loads(rej_path.read_text(encoding="utf-8"))) if rej_path.exists() else set()

    photos, total = {}, 0
    for s in SPECIES:
        sid = s["id"]
        m = meta.get(sid)
        if not m or sid in reject:
            continue
        p = RAW / m["path"]
        if not p.exists():
            continue
        uri, nbytes, size = encode(p)
        total += nbytes
        # CC BY-SA / パブリックドメイン等、ライセンスは記事とファイル名で辿れるようにする
        photos[sid] = [{
            "src": uri,
            "credit": f"Wikipedia: {m['article']} — {m['file']}",
            # 「写真のどこを見るか」の枠。0〜1の相対座標なので縮小しても崩れない。
            "boxes": ANNOTATIONS.get(sid, []),
        }]
        print(f"{sid:16s} {size[0]}x{size[1]:4d} {nbytes/1024:6.1f} KB")

    b64_mb = total * 4 / 3 / 1024 / 1024
    print(f"\n{len(photos)}種 / 元 {total/1024/1024:.2f} MB / base64換算 {b64_mb:.2f} MB")
    if b64_mb > BUDGET_MB:
        print(f"!! 予算 {BUDGET_MB} MB 超過。QUALITY か MAX_W を下げること")
    OUT.write_text(json.dumps(photos, ensure_ascii=False), encoding="utf-8")
    print("保存:", OUT)


if __name__ == "__main__":
    main()
