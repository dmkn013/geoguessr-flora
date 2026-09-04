# -*- coding: utf-8 -*-
"""座標がどの国かを判定する。

land.py は「陸か海か」だけだったが、
GeoGuessr のカバー国で絞るには国単位の判定が要る。

Natural Earth 110m の国境ポリゴン（data/countries110m.json）を使う。
110m は粗いので国境付近の点は取り違えうるが、
「どの国の点を残すか」という用途には十分。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402

_SRC = DATA / "countries110m.json"
_cache = None


def _decode(topo):
    """TopoJSON を経緯度のポリゴンに展開する。

    topojson ライブラリは入れず、必要な部分だけ自前で解く
    （依存を増やしたくない。land.py と同じ方針）。
    """
    tr = topo["transform"]
    sx, sy = tr["scale"]
    tx, ty = tr["translate"]

    def arc(i):
        rev = i < 0
        if rev:
            i = ~i
        pts, x, y = [], 0, 0
        for dx, dy in topo["arcs"][i]:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        return pts[::-1] if rev else pts

    def ring(idxs):
        out = []
        for i in idxs:
            seg = arc(i)
            out.extend(seg if not out else seg[1:])
        return out

    out = []
    for g in topo["objects"]["countries"]["geometries"]:
        name = (g.get("properties") or {}).get("name")
        if not name:
            continue
        polys = []
        if g["type"] == "Polygon":
            polys = [[ring(r) for r in g["arcs"]]]
        elif g["type"] == "MultiPolygon":
            polys = [[ring(r) for r in poly] for poly in g["arcs"]]
        # 外接矩形を先に持っておくと判定が速い（1万点×177国のため）
        for poly in polys:
            if not poly or not poly[0]:
                continue
            xs = [p[0] for p in poly[0]]
            ys = [p[1] for p in poly[0]]
            out.append((name, min(xs), min(ys), max(xs), max(ys), poly))
    return out


def load():
    global _cache
    if _cache is None:
        _cache = _decode(json.loads(_SRC.read_text(encoding="utf-8")))
    return _cache


def _inside(x, y, ring):
    """レイキャスティング。ring は [(lon, lat), ...]。"""
    n = len(ring)
    c = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            if x < (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi:
                c = not c
        j = i
    return c


def country_of(lat, lon):
    """その座標の国名（Natural Earth の name）。海なら None。"""
    for name, x0, y0, x1, y1, poly in load():
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        # poly[0] が外周、poly[1:] が穴
        if _inside(lon, lat, poly[0]):
            if any(_inside(lon, lat, h) for h in poly[1:]):
                continue
            return name
    return None
