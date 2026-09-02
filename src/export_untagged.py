# -*- coding: utf-8 -*-
"""未タグの画像を縮小してリポジトリに入れる（他の人に引き継ぐため）。

事情: 画像はローカルディスク（OneDrive同期外）に置いていて git に入れていない。
そのままでは clone しただけの人がタグ付けできない。
未タグ分だけを、タグ付けに必要な解像度まで落として同梱する。

サイズ: 元は1枚91KB×3,742枚＝331MB。
       640px/JPEG80 に落とすと1枚39KB＝141MBでGitHubに入る。
       タグ付けのシートは620px幅なので、この解像度で情報は落ちない。
"""
import json
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DATA  # noqa: E402

SRC = CANDIDATES.parent / "random"
OUT = DATA / "untagged"
MAX = 640
QUALITY = 80


def main():
    OUT.mkdir(exist_ok=True)
    tags = json.loads((DATA / "tags.json").read_text(encoding="utf-8"))
    idx = json.loads((DATA / "random_index.json").read_text(encoding="utf-8"))
    todo = [x for x in idx if x["img_id"] not in tags]

    n, tot, miss = 0, 0, 0
    for x in todo:
        src = SRC / x["file"]
        if not src.exists():
            miss += 1
            continue
        dst = OUT / x["file"]
        if dst.exists():
            tot += dst.stat().st_size
            n += 1
            continue
        im = Image.open(src).convert("RGB")
        im.thumbnail((MAX, MAX), Image.LANCZOS)
        im.save(dst, "JPEG", quality=QUALITY, optimize=True)
        tot += dst.stat().st_size
        n += 1
        if n % 500 == 0:
            print(f"  {n}/{len(todo)}", flush=True)

    print(f"{n}枚 / {tot / 1048576:.0f} MB → {OUT}")
    if miss:
        print(f"元画像が無い: {miss}枚")


if __name__ == "__main__":
    main()
