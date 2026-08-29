# -*- coding: utf-8 -*-
"""生成した SVG パスを PIL で描いて、本当に世界地図になっているか目視確認する。

（推定で「できたはず」と報告しないための検算。実際に描いて見る。）
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DATA, DIST  # noqa: E402
SP = DATA
d = (SP / "land_path.txt").read_text(encoding="utf-8")

W, H = 1000, 500
img = Image.new("RGB", (W, H), (18, 26, 38))
dr = ImageDraw.Draw(img)

rings = [r for r in d.split("Z") if r.strip()]
num = re.compile(r"(-?[\d.]+),(-?[\d.]+)")
drawn = 0
for r in rings:
    # 日付変更線対策でリング内を M で切っているので、サブパスごとに描く。
    # ここを無視して全点を1つのポリゴンにすると、切ったはずの帯がプレビューだけに現れる
    # （＝データではなく検証ツールが嘘をつく）。
    for sub in r.split("M"):
        if not sub.strip():
            continue
        pts = [(float(x) / 2, float(y) / 2) for x, y in num.findall(sub)]
        if len(pts) >= 3:
            dr.polygon(pts, fill=(72, 96, 78), outline=(120, 150, 125))
            drawn += 1

# 緯度の目安線（赤道・回帰線）
for lat, color in ((0, (220, 90, 90)), (23.44, (200, 160, 80)), (-23.44, (200, 160, 80))):
    y = (84.0 - lat) / (84.0 - (-56.0)) * H
    dr.line([(0, y), (W, y)], fill=color, width=1)

img.save(DIST / "map_preview.png")
print(f"描画リング {drawn}/{len(rings)} → {SP / 'map_preview.png'}")
