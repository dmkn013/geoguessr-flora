# -*- coding: utf-8 -*-
"""注釈の枠を実際に描画して、指している場所が合っているか目視する。

枠は手で決めるので、必ず描いて確かめる。
「たぶんこの辺」で入れた枠がずれていると、教材としては
何も無いより悪い（間違った場所を自信ありげに指すことになる）。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from annotations import ANNOTATIONS  # noqa: E402
from paths import DATA, DIST  # noqa: E402
from review_photos import F_NAME, F_SUB  # noqa: E402
from species import SPECIES  # noqa: E402

RAW = DATA / "photos_raw"
META = json.loads((RAW / "_meta.json").read_text(encoding="utf-8"))
CELL = 420


def draw(sid):
    m = META[sid]
    im = Image.open(RAW / m["path"]).convert("RGB")
    im.thumbnail((CELL, CELL), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for a in ANNOTATIONS.get(sid, []):
        x, y, w, h = a["box"]
        box = [x * im.width, y * im.height, (x + w) * im.width, (y + h) * im.height]
        # 明暗どちらの写真でも見えるよう、白の縁取りの上に色を重ねる
        d.rectangle(box, outline=(255, 255, 255), width=5)
        d.rectangle(box, outline=(230, 90, 60), width=3)
        d.text((box[0] + 5, max(2, box[1] - 16)), a["label"], font=F_SUB,
               fill=(230, 90, 60), stroke_width=3, stroke_fill=(255, 255, 255))
    return im


def main():
    targets = sys.argv[1:] or list(ANNOTATIONS)
    if not targets:
        print("注釈がまだ無い"); return
    byid = {s["id"]: s for s in SPECIES}
    cells = []
    for sid in targets:
        im = draw(sid)
        cv = Image.new("RGB", (CELL, CELL + 40), (250, 249, 246))
        cv.paste(im, ((CELL - im.width) // 2, 0))
        dd = ImageDraw.Draw(cv)
        dd.text((6, CELL + 4), f"{byid[sid]['ja']} / {sid}", font=F_NAME, fill=(20, 20, 20))
        dd.text((6, CELL + 23), f"要: {byid[sid]['tells'][0][:40]}", font=F_SUB, fill=(90, 90, 90))
        cells.append(cv)
    cols = min(3, len(cells))
    rows = (len(cells) + cols - 1) // cols
    W, H = cells[0].size
    sheet = Image.new("RGB", (cols * W, rows * H), (255, 255, 255))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % cols) * W, (i // cols) * H))
    out = DIST / "annotation_check.png"
    sheet.save(out)
    print("保存:", out)


if __name__ == "__main__":
    main()
