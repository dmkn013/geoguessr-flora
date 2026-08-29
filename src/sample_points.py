# -*- coding: utf-8 -*-
"""分布域の矩形から点をサンプリングし、陸地に載ったものだけ残す。

海に点が出るのを防ぐため、地図に使っているのと同じ陸地ポリゴンで判定する
（別ソースを使うと「地図では海なのに点がある」というズレが出る）。
"""
import json
import math
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from ranges import RANGES  # noqa: E402
from species import SPECIES  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DATA, DIST  # noqa: E402
SP = DATA
TARGET_TOTAL = 2800
random.seed(20260829)          # 再現性のため固定


# ---- 陸地ポリゴン（TopoJSON から経緯度のまま取り出す） ----
def load_land():
    topo = json.loads((SP / "world110m.json").read_text(encoding="utf-8"))
    tr = topo["transform"]
    sx, sy = tr["scale"]
    tx, ty = tr["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def arc_pts(i):
        return list(reversed(arcs[~i])) if i < 0 else arcs[i]

    rings = []
    for geom in topo["objects"]["land"]["geometries"]:
        polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
        for poly in polys:
            for ring in poly:
                pts = []
                for k, aid in enumerate(ring):
                    seg = arc_pts(aid)
                    pts.extend(seg[1:] if k else seg)
                if len(pts) >= 4:
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    rings.append((min(xs), max(xs), min(ys), max(ys), pts))
    return rings


LAND = load_land()
print(f"陸地リング: {len(LAND)}")


def on_land(lon, lat):
    for x0, x1, y0, y1, pts in LAND:
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue                       # bbox で先に落とす（速度のため）
        inside = False
        n = len(pts)
        j = n - 1
        for i in range(n):
            xi, yi = pts[i]
            xj, yj = pts[j]
            if (yi > lat) != (yj > lat):
                xc = (xj - xi) * (lat - yi) / (yj - yi) + xi
                if lon < xc:
                    inside = not inside
            j = i
        if inside:
            return True
    return False


# ---- 種ごとにサンプリング ----
total_w = sum(sum(b[4] for b in RANGES[s["id"]]) for s in SPECIES)
out = {}
report = []
for s in SPECIES:
    boxes = RANGES[s["id"]]
    w = sum(b[4] for b in boxes)
    quota = max(18, round(TARGET_TOTAL * w / total_w))
    pts = []
    for (la0, la1, lo0, lo1, bw) in boxes:
        want = max(3, round(quota * bw / w))
        tries = 0
        got = 0
        while got < want and tries < want * 220:
            tries += 1
            lat = random.uniform(la0, la1)
            lon = random.uniform(lo0, lo1)
            if not on_land(lon, lat):
                continue
            # 近すぎる点は間引く（同じ場所に固まらないように）
            if any(abs(lat - a) < 0.30 and abs(lon - b) < 0.30 for a, b in pts):
                continue
            pts.append((round(lat, 3), round(lon, 3)))
            got += 1
    out[s["id"]] = pts
    report.append((s["ja"], quota, len(pts)))

Path(DATA / "points.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

total = sum(len(v) for v in out.values())
print(f"生成点数: {total}")
short = [r for r in report if r[2] < r[1] * 0.75]
if short:
    print("目標に届かなかった種（分布矩形が海に寄っている可能性）:")
    for ja, q, g in sorted(short, key=lambda r: r[2] / r[1]):
        print(f"  {ja}: {g}/{q}")
else:
    print("全種が目標点数を概ね確保")
