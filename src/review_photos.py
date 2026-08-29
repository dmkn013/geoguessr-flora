# -*- coding: utf-8 -*-
"""取得した画像を一覧のコンタクトシートにして、目視確認できるようにする。

前回コルクガシで「記事の代表画像に肝心の特徴が写っていない」という失敗をした。
**48種すべて1枚ずつ目視する**のが前提なので、1枚ずつ開くのではなく
まとめて見られる形にする。種名と、その種の"見るべき特徴"を画像の脇に書くので、
「この写真にその特徴が写っているか」だけを判定すればよい。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from palette import assign  # noqa: E402
from paths import DATA, DIST  # noqa: E402
from species import SPECIES  # noqa: E402

assign(SPECIES)  # color は palette.py が実行時に割り当てる

RAW = DATA / "photos_raw"
META = json.loads((RAW / "_meta.json").read_text(encoding="utf-8"))

CELL_W, CELL_H = 300, 300      # 画像枠
CAP_H = 62                      # キャプション帯
COLS = 6
PAD = 8


def font(size):
    for name in ("meiryo.ttc", "YuGothM.ttc", "msgothic.ttc", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_NAME, F_SUB = font(17), font(13)


def cell(s):
    """1種分のセル画像。画像＋種名＋見分け方の要点。"""
    img = Image.new("RGB", (CELL_W, CELL_H + CAP_H), (250, 249, 246))
    m = META.get(s["id"])
    if m and (RAW / m["path"]).exists():
        ph = Image.open(RAW / m["path"]).convert("RGB")
        ph.thumbnail((CELL_W - PAD * 2, CELL_H - PAD * 2), Image.LANCZOS)
        img.paste(ph, ((CELL_W - ph.width) // 2, (CELL_H - ph.height) // 2))
    else:
        d0 = ImageDraw.Draw(img)
        d0.text((CELL_W // 2 - 30, CELL_H // 2), "なし", font=F_NAME, fill=(190, 60, 60))

    d = ImageDraw.Draw(img)
    d.rectangle([0, CELL_H, CELL_W, CELL_H + CAP_H], fill=(238, 236, 230))
    c = s["color"].lstrip("#")
    d.rectangle([6, CELL_H + 8, 16, CELL_H + 18],
                fill=tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)))
    d.text((22, CELL_H + 5), f"{s['ja']} / {s['id']}", font=F_NAME, fill=(20, 20, 20))
    # 見分け方の1つ目 = この写真に写っていてほしいもの
    tell = s["tells"][0][:34]
    d.text((6, CELL_H + 27), f"要: {tell}", font=F_SUB, fill=(70, 70, 70))
    art = (m or {}).get("article", "—")[:36]
    d.text((6, CELL_H + 44), f"記事: {art}", font=F_SUB, fill=(120, 120, 120))
    d.rectangle([0, 0, CELL_W - 1, CELL_H + CAP_H - 1], outline=(205, 202, 195))
    return img


def main():
    cells = [cell(s) for s in SPECIES]
    rows = (len(cells) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL_W, rows * (CELL_H + CAP_H)), (255, 255, 255))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % COLS) * CELL_W, (i // COLS) * (CELL_H + CAP_H)))
    # 1枚が巨大だと見づらいので上下2分割でも出す
    out = DIST / "photo_review.png"
    sheet.save(out)
    half = rows // 2 * (CELL_H + CAP_H)
    sheet.crop((0, 0, sheet.width, half)).save(DIST / "photo_review_1.png")
    sheet.crop((0, half, sheet.width, sheet.height)).save(DIST / "photo_review_2.png")
    print("保存:", out, f"({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
