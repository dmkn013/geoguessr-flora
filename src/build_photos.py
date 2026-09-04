# -*- coding: utf-8 -*-
"""トップページ用の写真を dist/photos/ へ置く。

base64 をやめて個別の JPEG にした理由:
  - base64 は 1.37 倍に膨らむ。元画質で置くなら無視できない差になる
  - JPEG ならブラウザのキャッシュが効き、2回目以降は転送が要らない
  - タイル JSON だと1枚見るのに数MBまとめて落とすことになる

**全 10,001 点**を置く（約890MB）。
最初は植物ありの 2,980 点だけにしていたが、履歴から使わなくなった
画像（data/untagged 等 191MB）を落として余地を作り、全点に広げた。
「植物なし」の点も、何が写っていて何が識別できなかったのかを
確かめられる方が調査として筋が通る。

元画質のままコピーする。1024x768 / 平均92KB。
全天球は中央を切り出す（そのままだと極端な横長で見づらい）。
"""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DATA, DIST  # noqa: E402

SRC = CANDIDATES.parent / "random"
OUT = DIST / "photos"


def main():
    tags = json.loads((DATA / "tags.json").read_text(encoding="utf-8"))
    idx = {x["img_id"]: x for x in
           json.loads((DATA / "random_index.json").read_text(encoding="utf-8"))}

    todo = [i for i in tags if i in idx]
    OUT.mkdir(parents=True, exist_ok=True)

    n = cropped = 0
    for img_id in todo:
        f = SRC / idx[img_id]["file"]
        if not f.exists():
            continue
        dst = OUT / f"{img_id}.jpg"
        if dst.exists():
            n += 1
            continue
        im = Image.open(f)
        if im.width / im.height > 1.9:
            # 全天球。そのまま出すと極端な横長で、何が写っているか読めない
            im = im.convert("RGB")
            cw = int(im.height * 1.6)
            im.crop(((im.width - cw) // 2, 0,
                     (im.width + cw) // 2, im.height)).save(
                dst, "JPEG", quality=88, optimize=True)
            cropped += 1
        else:
            shutil.copyfile(f, dst)      # 再圧縮しない（劣化させない）
        n += 1
        if n % 500 == 0:
            print(f"  {n}/{len(todo)}", flush=True)

    tot = sum(f.stat().st_size for f in OUT.glob("*.jpg")) / 1048576
    print(f"{n}枚 / {tot:.0f} MB → {OUT}（うち全天球の切り出し {cropped}枚）")


if __name__ == "__main__":
    main()
