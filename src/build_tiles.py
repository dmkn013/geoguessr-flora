# -*- coding: utf-8 -*-
"""全10,001点のサムネイルを、緯度経度のタイルに分けて書き出す。

タグ別（build_thumbs.py）と違い、こちらは**タグを選ばずに
どの点でもタップできる**トップページ用。

なぜタイルか:
  全点だと42MB。1ファイルでは重すぎる。タグ別に割ると
  「植物なし」7,028点が行き場を失う。
  地理で割れば、タップした場所の周辺だけ取りに行ける。

タイルの大きさ:
  15度四方。点は陸地に偏るので、実際に中身があるのは130前後。
  最大でも1.5MB程度に収まる（30度だと東アジアが6.1MBあった）。
"""
import base64
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DATA, DIST  # noqa: E402

SRC = CANDIDATES.parent / "random"
OUT = DIST / "tiles"
SIZE = 200
QUALITY = 56
# 30度だと東アジアのタイルが6.1MBになりモバイルで重かった。
# 15度に割ると最大1.5MB程度に収まる。
STEP = 15          # タイルの一辺（度）


def tile_of(lat, lon):
    return f"{int((lon + 180) // STEP)}_{int((lat + 90) // STEP)}"


def main():
    tags = json.loads((DATA / "tags.json").read_text(encoding="utf-8"))
    idx = {x["img_id"]: x for x in
           json.loads((DATA / "random_index.json").read_text(encoding="utf-8"))}

    groups = defaultdict(list)
    for img_id in tags:
        it = idx.get(img_id)
        if it:
            groups[tile_of(it["lat"], it["lon"])].append(img_id)

    OUT.mkdir(parents=True, exist_ok=True)
    done = 0
    for key, ids in sorted(groups.items(), key=lambda x: -len(x[1])):
        shots = {}
        for img_id in ids:
            f = SRC / idx[img_id]["file"]
            if not f.exists():
                continue
            im = Image.open(f).convert("RGB")
            if im.width / im.height > 1.9:
                cw = int(im.height * 1.6)
                im = im.crop(((im.width - cw) // 2, 0,
                              (im.width + cw) // 2, im.height))
            im.thumbnail((SIZE, SIZE), Image.LANCZOS)
            b = io.BytesIO()
            im.save(b, "JPEG", quality=QUALITY, optimize=True)
            shots[img_id] = base64.b64encode(b.getvalue()).decode()
        if not shots:
            continue
        (OUT / f"{key}.json").write_text(
            json.dumps(shots, separators=(",", ":")), encoding="utf-8")
        done += len(shots)
        print(f"  {key:6s} {len(shots):5d}枚  "
              f"{(OUT / f'{key}.json').stat().st_size/1048576:5.2f} MB", flush=True)

    tot = sum(f.stat().st_size for f in OUT.glob("*.json")) / 1048576
    print(f"\n{len(list(OUT.glob('*.json')))}タイル / {done}枚 / 合計 {tot:.0f} MB")


if __name__ == "__main__":
    main()
