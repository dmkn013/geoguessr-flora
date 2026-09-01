# -*- coding: utf-8 -*-
"""判定用のコンタクトシートを作り、判定結果を記録する。

判定はこちら（Claude）が画像を見て行う。
種ごとに未判定の写真を並べ、番号を振ったシートを出す。

    python src/judge_sheet.py sheet eucalyptus        # 未判定を12枚ずつ出す
    python src/judge_sheet.py sheet eucalyptus 2      # 2ページ目
    python src/judge_sheet.py ok  eucalyptus 0 3 7    # 採用
    python src/judge_sheet.py ng  eucalyptus 1 2 4    # 却下
    python src/judge_sheet.py todo                    # 残りの一覧

番号はページ内の通し番号（0始まり）。ページを出すたびに
「そのページに何が載っているか」を _page.json に記録するので、
ok/ng はその対応表を見て正しい画像に当たる。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DIST  # noqa: E402
from review_photos import F_NAME, F_SUB  # noqa: E402
from species import SPECIES  # noqa: E402
from verify_points import load_state, save_state  # noqa: E402

BYID = {s["id"]: s for s in SPECIES}
PAGE = DIST / "_page.json"
# 1シートの枚数。実際に判定してみて、この密度でも
# 樹形・葉の色・樹皮・林床の空き具合は読み取れることを確認した。
PER = 20
CELL = 330


def pending(sid):
    p = CANDIDATES / sid / "_pending.json"
    if not p.exists():
        return []
    items = json.loads(p.read_text(encoding="utf-8"))
    st = load_state(sid)
    done = {i["img_id"] for i in st["accepted"]} | {i["img_id"] for i in st["rejected"]}
    return [i for i in items if i["img_id"] not in done]


def sheet(sid, page=1):
    items = pending(sid)
    if not items:
        print(f"{sid}: 未判定なし")
        return
    s = BYID[sid]
    start = (page - 1) * PER
    chunk = items[start:start + PER]
    if not chunk:
        print(f"{sid}: ページ{page}は空（未判定 {len(items)}枚）")
        return
    cells = []
    for i, it in enumerate(chunk):
        f = CANDIDATES / sid / it["file"]
        im = Image.open(f).convert("RGB")
        # 横長パノラマは中央だけ切り出す。全天球を平面に開いた画像は
        # 端が歪んでいて判定しにくいため。
        if im.width / im.height > 1.9:
            w = int(im.height * 1.6)
            im = im.crop(((im.width - w) // 2, 0, (im.width + w) // 2, im.height))
        im.thumbnail((CELL, CELL), Image.LANCZOS)
        cv = Image.new("RGB", (CELL, CELL + 20), (250, 249, 246))
        cv.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
        d = ImageDraw.Draw(cv)
        d.rectangle([2, 2, 34, 22], fill=(20, 20, 20))
        d.text((9, 4), str(i), font=F_NAME, fill=(255, 255, 255))
        d.text((40, 5), f"{it['lat']:.2f},{it['lon']:.2f}", font=F_SUB, fill=(90, 90, 90))
        cells.append(cv)
    cols = 5
    rows = (len(cells) + cols - 1) // cols
    W, H = cells[0].size
    sh = Image.new("RGB", (cols * W, rows * H), (255, 255, 255))
    for i, c in enumerate(cells):
        sh.paste(c, ((i % cols) * W, (i // cols) * H))
    out = DIST / f"judge_{sid}.png"
    sh.save(out)
    PAGE.write_text(json.dumps(
        {"sid": sid, "page": page, "ids": [i["img_id"] for i in chunk]},
        ensure_ascii=False), encoding="utf-8")
    print(f"{out}  ({len(chunk)}枚 / 未判定 {len(items)}枚)")
    print(f"■ {s['ja']}（{s['sci']}）")
    print(f"  写っていれば採用: {' / '.join(s['tells'])}")
    print(f"  罠: {s['trap'][:110]}")


def decide(sid, nums, ok):
    # 種ごとのページ情報を優先（並列判定のため種別に分けている）
    p = DIST / f"_page_{sid}.json"
    if not p.exists():
        p = PAGE
    if not p.exists():
        print("先に sheet を出す")
        return
    pg = json.loads(p.read_text(encoding="utf-8"))
    if pg["sid"] != sid:
        print(f"直近のシートは {pg['sid']}。{sid} のシートを出し直す")
        return
    items = {i["img_id"]: i for i in json.loads(
        (CANDIDATES / sid / "_pending.json").read_text(encoding="utf-8"))}
    st = load_state(sid)
    have = {i["img_id"] for i in st["accepted"]} | {i["img_id"] for i in st["rejected"]}
    n = 0
    for x in nums:
        x = int(x)
        if x >= len(pg["ids"]):
            print(f"  [{x}] 範囲外")
            continue
        img = pg["ids"][x]
        if img in have or img not in items:
            continue
        (st["accepted"] if ok else st["rejected"]).append(items[img])
        n += 1
    save_state(sid, st)
    print(f"{sid}: {'採用' if ok else '却下'} {n}件 → "
          f"計 採用{len(st['accepted'])} 却下{len(st['rejected'])} "
          f"残り{len(pending(sid))}")


def todo():
    tot = 0
    for s in SPECIES:
        n = len(pending(s["id"]))
        if n:
            print(f"{s['id']:16s}{s['ja']:14s} {n:3d}枚")
            tot += n
    print(f"\n未判定 合計 {tot}枚")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    c = sys.argv[1]
    if c == "sheet" and len(sys.argv) > 2:
        sheet(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    elif c in ("ok", "ng") and len(sys.argv) > 3:
        decide(sys.argv[2], sys.argv[4:] if False else sys.argv[3:], c == "ok")
    elif c == "todo":
        todo()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
