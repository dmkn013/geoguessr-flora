# -*- coding: utf-8 -*-
"""写真に0.1刻みのグリッドを重ねて出す。注釈の枠座標を読み取るための道具。

    python src/grid_sheet.py oilpalm doum cecropia
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA, DIST  # noqa: E402

RAW = DATA / "photos_raw"
META = json.loads((RAW / "_meta.json").read_text(encoding="utf-8"))
C = 380

ids = sys.argv[1:]
cells = []
for sid in ids:
    im = Image.open(RAW / META[sid]["path"]).convert("RGB")
    im.thumbnail((C, C), Image.LANCZOS)
    cv = Image.new("RGB", (C, C + 18), (255, 255, 255))
    cv.paste(im, ((C - im.width) // 2, 0))
    d = ImageDraw.Draw(cv)
    ox = (C - im.width) // 2
    for i in range(1, 10):
        col = (255, 0, 0) if i == 5 else (120, 200, 255)
        d.line([(ox + im.width * i / 10, 0), (ox + im.width * i / 10, im.height)], fill=col)
        d.line([(ox, im.height * i / 10), (ox + im.width, im.height * i / 10)], fill=col)
    d.text((3, C + 3), f"{sid}  {im.width}x{im.height}", fill=(0, 0, 0))
    cells.append(cv)

cols = min(3, len(cells))
rows = (len(cells) + cols - 1) // cols
W, H = cells[0].size
sh = Image.new("RGB", (cols * W, rows * H), (255, 255, 255))
for i, c in enumerate(cells):
    sh.paste(c, ((i % cols) * W, (i // cols) * H))
sh.save(DIST / "grid.png")
print("保存:", DIST / "grid.png")
