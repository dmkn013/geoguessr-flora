# -*- coding: utf-8 -*-
"""粗いタグを、写真だけを根拠に下位分類まで落とす。

tag_sheet.py との違い:
  - 対象は既にタグが付いた画像のうち、階層の粗いものだけ
  - **座標を表示しない**。ここが肝心。

なぜ座標を出さないか:
  GeoGuessr は写真から場所を当てるゲーム。座標を見て種を決めると
  「ブラジルだからパラナ松」となり、教材としては循環論法になる。
  それでは「パラナ松が見えたからブラジル」という推論に使えない。
  写真だけで判別できる範囲に留める（ユーザー指定）。

判別できなければ元のタグのままでよい。無理に落とすとデータが濁る。

ユーカリ属は特殊:
  種が700〜900あり、決め手（果実 gumnut、蕾の帽子 operculum）は
  数cmなので車載写真ではまず写らない。
  ただし**樹皮タイプ**は遠目に効き、種を跨ぐグループを示す。
  「アイアンバーク」（黒く深く裂ける）「レモンユーカリ」（幹が白く
  滑らかで細長い）は下位タグとして付けてよい（ユーザー判断）。

    python src/refine_sheet.py --w2 next
    python src/refine_sheet.py --w2 set 3 ヨーロッパアカマツ
    python src/refine_sheet.py --w2 keep 0 1 2     # 現状維持
    python src/refine_sheet.py stats
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
TAGS = DATA / "tags.json"
DONE = DATA / "refined.json"      # 見直し済みの画像ID（判別できたかは問わない）

# 階層が粗く、写真から下位に落とせる見込みのあるタグ
COARSE = {"ヤシ科", "マツ属", "ユーカリ属", "トウヒ属", "カバノキ属", "タケ亜科",
          "バショウ属", "アカシア属", "ポプラ属", "コナラ属", "イトスギ属",
          "ビャクシン属"}

PER = 4
CELL = 820        # 種の判別には葉や樹皮の細部が要る。タグ付けより大きく出す


def page_file(w=""):
    return DIST / f"_refpage{w}.json"


def load(path, default):
    if not path.exists():
        return default
    import time
    for i in range(5):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            if i == 4:
                raise
            time.sleep(0.2)
    return default


def save_atomic(path, obj):
    import os
    import time
    tmp = path.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    for i in range(10):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if i == 9:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.15)


def targets(w=""):
    """見直し対象。粗いタグが付いていて、まだ見直していないもの。"""
    tags = load(TAGS, {})
    done = set(load(DONE, []))
    idx = {x["img_id"]: x for x in load(INDEX, [])}
    busy = set()
    for f in DIST.glob("_refpage*.json"):
        if f.name == f"_refpage{w}.json":
            continue
        try:
            busy |= set(json.loads(f.read_text(encoding="utf-8"))["ids"])
        except Exception:
            pass
    out = [(i, v) for i, v in tags.items()
           if i in idx and i not in done and i not in busy
           and any(t in COARSE for t in v)]
    # 同じタグが固まると比較しやすい一方、判断が引きずられる。
    # タグ順に並べつつ、同じ地点の連写は散らす。
    out.sort(key=lambda x: (sorted(x[1]), x[0]))
    return out


def sheet(w=""):
    items = targets(w)
    if not items:
        print("完了: 見直す画像なし")
        return
    idx = {x["img_id"]: x for x in load(INDEX, [])}
    chunk = items[:PER]
    cells = []
    for n, (img_id, names) in enumerate(chunk):
        f = IMGDIR / idx[img_id]["file"]
        if not f.exists():
            continue
        im = Image.open(f).convert("RGB")
        if im.width / im.height > 1.9:
            cw = int(im.height * 1.6)
            im = im.crop(((im.width - cw) // 2, 0, (im.width + cw) // 2, im.height))
        im.thumbnail((CELL, CELL), Image.LANCZOS)
        cv = Image.new("RGB", (CELL, CELL + 24), (250, 249, 246))
        cv.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
        d = ImageDraw.Draw(cv)
        d.rectangle([2, 2, 34, 24], fill=(20, 20, 20))
        d.text((9, 4), str(n), font=F_NAME, fill=(255, 255, 255))
        # **座標は出さない**。出すと地理から逆算してしまう
        d.text((40, 6), " / ".join(names), font=F_SUB, fill=(90, 90, 90))
        cells.append(cv)
    if not cells:
        print("完了: 見直す画像なし")
        return
    cols = 2
    rows = (len(cells) + cols - 1) // cols
    W, H = cells[0].size
    sh = Image.new("RGB", (cols * W, rows * H), (255, 255, 255))
    for i, c in enumerate(cells):
        sh.paste(c, ((i % cols) * W, (i // cols) * H))
    out = DIST / f"refine_sheet{w}.png"
    sh.save(out)
    page_file(w).write_text(json.dumps(
        {"ids": [i for i, _ in chunk]}, ensure_ascii=False), encoding="utf-8")
    print(f"画像パス: {out}")
    print(f"枚数: {len(cells)}（残り {len(items)}枚）")
    for n, (img_id, names) in enumerate(chunk):
        print(f"  [{n}] 現在: {' / '.join(names)}")


def _ids(w):
    if not page_file(w).exists():
        print("先に next を実行")
        return None
    return json.loads(page_file(w).read_text(encoding="utf-8"))["ids"]


def setv(num, names, w=""):
    ids = _ids(w)
    if ids is None:
        return
    n = int(num)
    if n >= len(ids):
        print(f"[{n}] 範囲外")
        return
    lead = []
    rest = list(names)
    while rest and rest[0].isdigit():
        lead.append(rest.pop(0))
    if lead:
        print(f"!! set は1画像ずつです。番号 {num} {' '.join(lead)} をまとめています")
        for x in [num] + lead:
            print(f"     set {x} {' '.join(rest)}")
        return
    flat = []
    for x in names:
        for y in x.replace("、", ",").replace(",", " ").split():
            if y and not y.isdigit():
                flat.append(y)
    flat = list(dict.fromkeys(flat))
    if not flat:
        print("!! タグが空です。現状維持なら keep を使ってください")
        return
    tags = load(TAGS, {})
    tags[ids[n]] = flat
    save_atomic(TAGS, tags)
    done = set(load(DONE, []))
    done.add(ids[n])
    save_atomic(DONE, sorted(done))
    print(f"[{n}] → {' / '.join(flat)}")


def keep(nums, w=""):
    ids = _ids(w)
    if ids is None:
        return
    done = set(load(DONE, []))
    c = 0
    for x in nums:
        x = int(x)
        if x < len(ids):
            done.add(ids[x])
            c += 1
    save_atomic(DONE, sorted(done))
    print(f"{c}枚を「これ以上絞れない」として記録")


def stats():
    tags = load(TAGS, {})
    done = load(DONE, [])
    left = len(targets())
    from collections import Counter
    c = Counter(n for v in tags.values() for n in v)
    print(f"見直し済み {len(done)}枚 / 残り {left}枚")
    print(f"\n粗いタグの残り:")
    for t in sorted(COARSE, key=lambda x: -c.get(x, 0)):
        if c.get(t):
            print(f"  {t:12s}{c[t]:5d}")
    fine = {t: n for t, n in c.items() if t not in COARSE}
    print(f"\n細かいタグ {len(fine)}種類 / 延べ {sum(fine.values())}枚")


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
    elif cmd == "keep" and len(args) > 1:
        keep(args[1:], w)
    elif cmd == "stats":
        stats()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
