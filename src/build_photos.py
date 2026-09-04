# -*- coding: utf-8 -*-
"""トップページ用の写真を dist/photos/ へ置く。

base64 をやめて個別の JPEG にした理由:
  - base64 は 1.37 倍に膨らむ。元画質で置くなら無視できない差になる
  - JPEG ならブラウザのキャッシュが効き、2回目以降は転送が要らない
  - タイル JSON だと1枚見るのに数MBまとめて落とすことになる

**地図に出す点だけ**を置く。
条件は「属を特定できた」かつ「GeoGuessr のカバー国」。
地図から消した点の写真を置いても到達する手段がない（ユーザー判断）。

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

from coverage import is_covered  # noqa: E402
from paths import CANDIDATES, DATA, DIST  # noqa: E402

SRC = CANDIDATES.parent / "random"
OUT = DIST / "photos"


def main():
    tags = json.loads((DATA / "tags.json").read_text(encoding="utf-8"))
    idx = {x["img_id"]: x for x in
           json.loads((DATA / "random_index.json").read_text(encoding="utf-8"))}

    where = json.loads((DATA / "country_of.json").read_text(encoding="utf-8"))         if (DATA / "country_of.json").exists() else {}
    todo = [i for i, v in tags.items()
            if v and i in idx and is_covered(where.get(i) or "")]
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

    # 対象外になった写真を消す（タグ付けが進むと入れ替わる）
    keep = {f"{i}.jpg" for i in todo}
    gone = 0
    for f in OUT.glob("*.jpg"):
        if f.name not in keep:
            f.unlink()
            gone += 1

    tot = sum(f.stat().st_size for f in OUT.glob("*.jpg")) / 1048576
    print(f"{n}枚 / {tot:.0f} MB → {OUT}（全天球の切り出し {cropped}枚 / "
          f"対象外を削除 {gone}枚）")


if __name__ == "__main__":
    main()
