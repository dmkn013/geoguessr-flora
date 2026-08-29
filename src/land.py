# -*- coding: utf-8 -*-
"""陸地ポリゴンの読み込みと内外判定。

sample_points.py にあったものを切り出した。
あちらは import しただけで生成処理が走る（print も出る）スクリプトなので、
他から陸地判定だけ使いたいときに困る。

判定には**地図に使っているのと同じ**陸地ポリゴンを使う。
別ソースを使うと「地図では海なのに点がある」というズレが出る。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DATA  # noqa: E402


def load_land():
    topo = json.loads((DATA / "world110m.json").read_text(encoding="utf-8"))
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


def on_land(lon, lat, rings):
    for x0, x1, y0, y1, pts in rings:
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
