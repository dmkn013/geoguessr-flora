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
# 48種収集の1,918枚は**対象にしない**。
# あれは種の分布域から引いたもので、母集団が偏っている。
# 混ぜると「世界の道端で何%見えるか」という数字が壊れるため、
# ランダム収集分だけを扱う（ユーザー判断）。
TAGS = DATA / "tags.json"
# 並列でタグ付けすると同じシート情報を上書きして誤記録するので、
# ワーカーごとにファイルを分ける。第1引数の前に --w<N> を付けて指定。
def page_file(w=""):
    return DIST / f"_tagpage{w}.json"

PER = 9          # 3x3。詰めると見落とすので増やさない
CELL = 620


def load_tags():
    return json.loads(TAGS.read_text(encoding="utf-8")) if TAGS.exists() else {}


def save_tags(t):
    TAGS.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")


def load_index():
    """タグ付け対象。**ランダム収集分のみ**。"""
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []


def img_path(it):
    return IMGDIR / it["file"]


def untagged(w=""):
    """未タグの一覧。

    並列時は他ワーカーが今まさに見ているシートを避ける
    （二重にタグを付けても上書きされるだけだが、無駄なので）。
    """
    tags = load_tags()
    busy = set()
    for f in DIST.glob("_tagpage*.json"):
        if f.name == f"_tagpage{w}.json":
            continue
        try:
            busy |= set(json.loads(f.read_text(encoding="utf-8"))["ids"])
        except Exception:
            pass
    return [it for it in load_index()
            if it["img_id"] not in tags and it["img_id"] not in busy]


def sheet(w=""):
    items = untagged(w)
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
            # ここで w を使うとワーカーIDの w を潰してしまう（実際に踏んだ）
            cw = int(im.height * 1.6)
            im = im.crop(((im.width - cw) // 2, 0, (im.width + cw) // 2, im.height))
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
    out = DIST / f"tag_sheet{w}.png"
    sh.save(out)
    page_file(w).write_text(json.dumps(
        {"ids": [i["img_id"] for i in chunk]}, ensure_ascii=False), encoding="utf-8")
    print(f"画像パス: {out}")
    print(f"枚数: {len(cells)}（未タグ {len(items)}枚）")


def setv(num, names, w=""):
    if not page_file(w).exists():
        print("先に next を実行")
        return
    ids = json.loads(page_file(w).read_text(encoding="utf-8"))["ids"]
    n = int(num)
    if n >= len(ids):
        print(f"[{n}] 範囲外")
        return
    t = load_tags()
    t[ids[n]] = names
    save_tags(t)
    print(f"[{n}] → {' / '.join(names) if names else '（なし）'}")


def none(nums, w=""):
    if not page_file(w).exists():
        print("先に next を実行")
        return
    ids = json.loads(page_file(w).read_text(encoding="utf-8"))["ids"]
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
    t = load_tags()
    idx = load_index()
    from collections import Counter
    c = Counter()
    empty = 0
    for v in t.values():
        if not v:
            empty += 1
        for name in v:
            c[name] += 1
    print(f"タグ付け {len(t)} / 収集 {len(idx)}枚  （植物なし {empty}枚）")
    if not t:
        return
    print(f"\n出現率（タグ付け済み{len(t)}枚に対する割合）:")
    for name, n in c.most_common(30):
        print(f"  {name:22s}{n:4d}  ({n / len(t) * 100:.1f}%)")
    print(f"\n異なるタグ {len(c)}種類")


def main():
    args = sys.argv[1:]
    w = ""
    if args and args[0].startswith("--w"):
        w = args[0][3:]
        args = args[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "next":
        sheet(w)
    elif cmd == "set" and len(args) > 1:
        setv(args[1], args[2:], w)
    elif cmd == "none" and len(args) > 1:
        none(args[1:], w)
    elif cmd == "stats":
        stats()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
