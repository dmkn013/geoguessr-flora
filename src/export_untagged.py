# -*- coding: utf-8 -*-
"""未タグの画像をリポジトリに入れる（他の人に引き継ぐため）。

事情: 画像はローカルディスク（OneDrive同期外）に置いていて git に入れていない。
そのままでは clone しただけの人がタグ付けできない。

**元画質のままコピーする**（ユーザー指定）。
以前は640pxに縮小していたが、種の判別には樹皮の細部が要るため
解像度を落とさない。1024x768 / 平均92KB。

置き場所は untagged ブランチ。main の履歴を汚さないため
（過去に main へ入れて .git が膨らみ、履歴を書き換えて掃除した）。
"""
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DATA  # noqa: E402

SRC = CANDIDATES.parent / "random"
OUT = DATA / "untagged"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
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
        if not dst.exists():
            shutil.copyfile(src, dst)      # 再圧縮しない
        tot += dst.stat().st_size
        n += 1
        if n % 1000 == 0:
            print(f"  {n}/{len(todo)}", flush=True)

    print(f"{n}枚 / {tot / 1048576:.0f} MB → {OUT}")
    if miss:
        print(f"元画像が無い: {miss}枚")


if __name__ == "__main__":
    main()
