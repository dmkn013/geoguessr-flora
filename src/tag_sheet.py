# -*- coding: utf-8 -*-
"""ランダム収集した画像にタグを付ける。

前回の judge_one.py（種を決めてYES/NO）とは形式が違う:
  - 1枚に**複数タグ**が付く
  - 語彙は固定しない。**新しい植物は自由にタグを作ってよい**
  - 「草地」「針葉樹林」のような植生タイプは付けない。
    **識別できる植物名**（属または種）だけを付ける。

粒度の方針（ユーザー指定）:
  **属レベルを基本とし、種まで分かれば種も付ける。**
    例) 北欧の針葉樹林で幹がオレンジ → 「マツ属」＋「ヨーロッパアカマツ」
        遠景で属しか分からない       → 「マツ属」だけ
        葉形まで見える豪州の木       → 「ユーカリ属」
  「針葉樹林」「広葉樹林」は植生タイプなので付けない。
  「マツ属」は分類群なので付けてよい。この線引きを守る。

    python src/tag_sheet.py next              # 次のシートを出す
    python src/tag_sheet.py set 3 ユーカリ バナナ   # 3番にタグを付ける
    python src/tag_sheet.py none 0 1 2         # 植物が識別できない
    python src/tag_sheet.py stats              # 集計

「植物が写っていない」と「写っているが種を特定できない」は区別する。
前者は none、後者はタグを付けずに skip（後で見直せるように残す）。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DATA, DIST  # noqa: E402
from review_photos import F_NAME, F_SUB  # noqa: E402

IMGDIR = CANDIDATES.parent / "random"
INDEX = DATA / "random_index.json"
# 48種収集で集めた1,918枚も同じ車載写真なので捨てずにタグ付けする。
# ただし**出自が違う**（種の分布域から引いたので母集団が偏る）。
# 遭遇率の分母を汚さないよう source を分けて記録する。
SPECIES_INDEX = DATA / "species_index.json"
TAGS = DATA / "tags.json"
PAGE = DIST / "_tagpage.json"

PER = 9          # 3x3。詰めると見落とすので増やさない
CELL = 620


def load_tags():
    return json.loads(TAGS.read_text(encoding="utf-8")) if TAGS.exists() else {}


def save_tags(t):
    TAGS.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")


def load_index():
    """タグ付け対象の一覧。ランダム分と48種収集分の両方。

    source を持たせて出自を区別する:
      "random"  = 世界から一様に引いた（遭遇率の母集団になる）
      "species" = 48種の分布域から引いた（母集団が偏るので別集計）
    """
    out = []
    if INDEX.exists():
        for it in json.loads(INDEX.read_text(encoding="utf-8")):
            it["source"] = "random"
            out.append(it)
    if SPECIES_INDEX.exists():
        for it in json.loads(SPECIES_INDEX.read_text(encoding="utf-8")):
            it["source"] = "species"
            out.append(it)
    return out


def img_path(it):
    """出自に応じて実ファイルの場所を返す。"""
    if it.get("source") == "species":
        return CANDIDATES / it["sp"] / it["file"]
    return IMGDIR / it["file"]


def untagged():
    tags = load_tags()
    return [it for it in load_index() if it["img_id"] not in tags]


def sheet():
    items = untagged()
    if not items:
        print("完了: 未タグの画像なし")
        return
    chunk = items[:PER]
    cells = []
    for i, it in enumerate(chunk):
        f = img_path(it)
        if not f.exists():
            continue
        im = Image.open(f).convert("RGB")
        if im.width / im.height > 1.9:      # 全天球は中央だけ
            w = int(im.height * 1.6)
            im = im.crop(((im.width - w) // 2, 0, (im.width + w) // 2, im.height))
        im.thumbnail((CELL, CELL), Image.LANCZOS)
        cv = Image.new("RGB", (CELL, CELL + 22), (250, 249, 246))
        cv.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
        d = ImageDraw.Draw(cv)
        d.rectangle([2, 2, 34, 24], fill=(20, 20, 20))
        d.text((9, 4), str(i), font=F_NAME, fill=(255, 255, 255))
        d.text((40, 6), f"{it['lat']:.2f},{it['lon']:.2f}", font=F_SUB, fill=(90, 90, 90))
        cells.append(cv)
    cols = 3
    rows = (len(cells) + cols - 1) // cols
    W, H = cells[0].size
    sh = Image.new("RGB", (cols * W, rows * H), (255, 255, 255))
    for i, c in enumerate(cells):
        sh.paste(c, ((i % cols) * W, (i // cols) * H))
    out = DIST / "tag_sheet.png"
    sh.save(out)
    PAGE.write_text(json.dumps(
        {"ids": [i["img_id"] for i in chunk]}, ensure_ascii=False), encoding="utf-8")
    print(f"画像パス: {out}")
    print(f"枚数: {len(cells)}（未タグ {len(items)}枚）")


def setv(num, names):
    if not PAGE.exists():
        print("先に next を実行")
        return
    ids = json.loads(PAGE.read_text(encoding="utf-8"))["ids"]
    n = int(num)
    if n >= len(ids):
        print(f"[{n}] 範囲外")
        return
    t = load_tags()
    t[ids[n]] = names
    save_tags(t)
    print(f"[{n}] → {' / '.join(names) if names else '（なし）'}")


def none(nums):
    if not PAGE.exists():
        print("先に next を実行")
        return
    ids = json.loads(PAGE.read_text(encoding="utf-8"))["ids"]
    t = load_tags()
    c = 0
    for x in nums:
        x = int(x)
        if x < len(ids):
            t[ids[x]] = []
            c += 1
    save_tags(t)
    print(f"{c}枚を「識別できる植物なし」として記録")


def stats():
    """出自ごとに分けて集計する。

    ランダム収集と48種収集は**母集団が違う**。
    後者は種の分布域から引いているので、その種が出やすいのは当たり前で、
    混ぜると「世界の道端で何%見えるか」の数字が壊れる。
    """
    t = load_tags()
    idx = load_index()
    src = {it["img_id"]: it.get("source", "random") for it in idx}
    from collections import Counter
    per = {"random": Counter(), "species": Counter()}
    done = {"random": 0, "species": 0}
    empty = {"random": 0, "species": 0}
    for k, v in t.items():
        s = src.get(k, "random")
        done[s] += 1
        if not v:
            empty[s] += 1
        for name in v:
            per[s][name] += 1
    tot = {s: sum(1 for it in idx if it.get("source", "random") == s)
           for s in ("random", "species")}
    for s, label in (("random", "ランダム収集（世界一様・遭遇率の母集団）"),
                     ("species", "48種収集（分布域から抽出・母集団が偏る）")):
        if not tot[s]:
            continue
        print(f"\n■ {label}")
        print(f"  タグ付け {done[s]} / {tot[s]}枚  （植物なし {empty[s]}枚）")
        for name, n in per[s].most_common(20):
            print(f"    {name:22s}{n:4d}  ({n / max(1, done[s]) * 100:.1f}%)")
        print(f"    異なるタグ {len(per[s])}種類")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "next":
        sheet()
    elif cmd == "set" and len(sys.argv) > 2:
        setv(sys.argv[2], sys.argv[3:])
    elif cmd == "none" and len(sys.argv) > 2:
        none(sys.argv[2:])
    elif cmd == "stats":
        stats()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
