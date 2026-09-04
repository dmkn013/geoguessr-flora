# -*- coding: utf-8 -*-
"""国境線の SVG パスを作る。

地図に陸地の輪郭しか無いと、点がどの国かを目で追えない。
countries50m.json（countries.py が国判定に使うのと同じデータ）から
国境を引く。

投影は build_tagmap.project と同じ正距円筒。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402

VIEW_W, VIEW_H = 2000.0, 1000.0
LAT_TOP, LAT_BOTTOM = 84.0, -56.0     # build_tagmap と合わせること


def _project(lon, lat):
    x = (lon + 180.0) / 360.0 * VIEW_W
    y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * VIEW_H
    return x, y


def path(simplify=0.35):
    """全ポリゴンの外周を線として返す。

    simplify: 度単位のしきい値。これ未満しか動いていない点は捨てる。
      50m は点が多く、そのまま出すと 1.5MB を超える。
    """
    topo = json.loads((DATA / "countries50m.json").read_text(encoding="utf-8"))
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

    out = []
    # 弧を単位に描く。ポリゴンごとに描くと共有する国境を二度引くことになる。
    for i in range(len(topo["arcs"])):
        pts = arc(i)
        if len(pts) < 2:
            continue
        d = []
        last = None
        for lon, lat in pts:
            if last and abs(lon - last[0]) < simplify and \
                    abs(lat - last[1]) < simplify:
                continue
            # 日付変更線をまたぐ線は描かない（地図を横断する帯になる）
            if last and abs(lon - last[0]) > 180:
                if len(d) > 1:
                    out.append("M" + "L".join(d))
                d = []
                last = None
                continue
            x, y = _project(lon, lat)
            d.append(f"{x:.1f},{y:.1f}")
            last = (lon, lat)
        if len(d) > 1:
            out.append("M" + "L".join(d))
    return "".join(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p = path()
    print(f"{len(p) / 1024:.0f} KB / {p.count('M')} 本")
