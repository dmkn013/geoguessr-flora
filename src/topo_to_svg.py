# -*- coding: utf-8 -*-
"""world-atlas の TopoJSON(land-110m) を SVG パス文字列へ変換する。

Artifact は外部ホストへ通信できない（地図タイルが使えない）ので、陸地の輪郭を
パスとして HTML に直接埋め込む必要がある。

投影は正距円筒（equirectangular）。理由:
- 緯度経度からピクセル座標への変換が1行で済むので、点の配置とホバー判定が単純になる
- 教材として「どの大陸か」が分かれば十分で、面積の正確さは要らない
高緯度が引き伸ばされるため、南極（-90〜-60）は切り落として縦の無駄を省く。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DATA, DIST  # noqa: E402
SP = DATA
topo = json.loads((SP / "world110m.json").read_text(encoding="utf-8"))

tr = topo["transform"]
sx, sy = tr["scale"]
tx, ty = tr["translate"]

# --- arc をデコード（デルタ符号化 + 量子化を戻す） ---
arcs = []
for arc in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx
        y += dy
        pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)


def arc_points(idx):
    if idx < 0:
        return list(reversed(arcs[~idx]))
    return arcs[idx]


# --- 投影 ---
VIEW_W, VIEW_H = 2000.0, 1000.0
LAT_TOP, LAT_BOTTOM = 84.0, -56.0     # 南極とグリーンランド最北を落として縦を詰める


def project(lon, lat):
    x = (lon + 180.0) / 360.0 * VIEW_W
    y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * VIEW_H
    return x, y


def ring_to_path(ring_arc_ids):
    pts = []
    for i, aid in enumerate(ring_arc_ids):
        seg = arc_points(aid)
        pts.extend(seg[1:] if i else seg)      # 連結部の重複点を落とす
    if len(pts) < 4:
        return ""

    # 表示緯度の外に完全に出ているリング（南極など）は捨てる。
    # クランプすると下端に横一直線の帯として描かれてしまう。
    if all(lat < LAT_BOTTOM for _lon, lat in pts):
        return ""

    out = []
    prev_lon = None
    pen_up = True                              # 次の点を M で置くか L で置くか
    for lon, lat in pts:
        # 日付変更線をまたぐと経度が +179 → -179 のように飛び、
        # 正距円筒では「地図を横断する一本の線」になる（フィジー約17°S・
        # チュクチ半島約70°N で実際に発生した）。飛んだらパスを切る。
        if prev_lon is not None and abs(lon - prev_lon) > 180.0:
            pen_up = True
        prev_lon = lon
        lat = max(LAT_BOTTOM - 4, min(LAT_TOP + 4, lat))
        x, y = project(lon, lat)
        out.append(f"{'M' if pen_up else 'L'}{x:.1f},{y:.1f}")
        pen_up = False
    return "".join(out) + "Z"


paths = []
for geom in topo["objects"]["land"]["geometries"]:
    polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
    for poly in polys:
        for ring in poly:
            p = ring_to_path(ring)
            if p:
                paths.append(p)

d = "".join(paths)
out = DATA / "land_path.txt"
out.write_text(d, encoding="utf-8")
print(f"リング数: {len(paths)}")
print(f"パス長: {len(d):,} 文字")
print(f"viewBox: 0 0 {VIEW_W:.0f} {VIEW_H:.0f}  (lat {LAT_TOP}..{LAT_BOTTOM})")
print("保存:", out)
