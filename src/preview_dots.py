# -*- coding: utf-8 -*-
"""tab10 の点が明・暗どちらの陸地色の上でも沈まないか、実際に描いて確かめる。

「たぶん見える」で済ませず、地図と同じ配色・同じ半径で描画して目視する。
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")

from palette import assign  # noqa: E402
from species import SPECIES  # noqa: E402

assign(SPECIES)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DATA, DIST  # noqa: E402
SP = DATA
d = (SP / "land_path.txt").read_text(encoding="utf-8")

THEMES = [
    ("light", (0xE4, 0xE1, 0xD9), (0xD6, 0xD5, 0xCD), (0xB3, 0xB2, 0xA9)),
    ("dark",  (0x0C, 0x11, 0x14), (0x2B, 0x32, 0x2F), (0x43, 0x4B, 0x47)),
]
W, H = 1200, 600
num = re.compile(r"(-?[\d.]+),(-?[\d.]+)")
LAT_TOP, LAT_BOT = 84.0, -56.0

tiles = []
for name, ocean, land, edge in THEMES:
    img = Image.new("RGB", (W, H), ocean)
    dr = ImageDraw.Draw(img)
    for ring in d.split("Z"):
        for sub in ring.split("M"):
            if not sub.strip():
                continue
            pts = [(float(x) * W / 2000, float(y) * H / 1000) for x, y in num.findall(sub)]
            if len(pts) >= 3:
                dr.polygon(pts, fill=land, outline=edge)
    import json
    PTS = json.loads((SP / "points.json").read_text(encoding="utf-8"))
    for s in SPECIES:
        c = s["color"].lstrip("#")
        rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
        for lat, lon in PTS[s["id"]]:
            x = (lon + 180) / 360 * W
            y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOT) * H
            r = 2.6
            dr.ellipse([x - r, y - r, x + r, y + r], fill=rgb, outline=ocean, width=1)
    tiles.append(img)

out = Image.new("RGB", (W, H * 2))
out.paste(tiles[0], (0, 0))
out.paste(tiles[1], (0, H))
out.save(DIST / "dots_preview.png")
print("保存:", DIST / "dots_preview.png")
