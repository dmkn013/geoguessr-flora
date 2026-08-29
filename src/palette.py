# -*- coding: utf-8 -*-
"""10色を「地理的に近い種が同色にならないように」割り当てる。

38色を全部分けても人間には見分けられないので、色の役割を
「種の識別」から「隣り合う種の区別」へ変える（地図の四色定理と同じ考え方）。
種の識別はホバー／クリックのラベルが担う。

手順:
 1. 種どうしの「近さ」を、アンカー点の最小距離で測る
 2. しきい値以内なら隣接とみなしてグラフを作る
 3. 次数の大きい順に貪欲彩色。衝突を避けられない場合は
    「同色の種が最も遠くなる色」を選ぶ（必ず解が出て、劣化が緩やか）
"""
import math

# matplotlib の tab10 をそのまま使う。
# 独自に配色を作るより、カテゴリカル配色として実績のあるものを使う方が確実。
PALETTE = [
    "#1f77b4",  # 青
    "#ff7f0e",  # 橙
    "#2ca02c",  # 緑
    "#d62728",  # 赤
    "#9467bd",  # 紫
    "#8c564b",  # 茶
    "#e377c2",  # 桃
    "#7f7f7f",  # 灰
    "#bcbd22",  # 黄緑
    "#17becf",  # 水色
]

ADJACENT_DEG = 20.0   # この距離以内に点があれば「隣接」とみなす


def _dist(a, b):
    """経度は緯度に応じて縮むので cos 補正した簡易距離（度）。"""
    la1, lo1 = a
    la2, lo2 = b
    dlat = la1 - la2
    dlon = (lo1 - lo2) * math.cos(math.radians((la1 + la2) / 2))
    # 日付変更線をまたぐ場合は短い方を採る
    if abs(lo1 - lo2) > 180:
        dlon = (360 - abs(lo1 - lo2)) * math.cos(math.radians((la1 + la2) / 2))
    return math.hypot(dlat, dlon)


def min_dist(sp_a, sp_b):
    return min(_dist(a, b) for a in sp_a["anchors"] for b in sp_b["anchors"])


def assign(species):
    n = len(species)
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d[i][j] = d[j][i] = min_dist(species[i], species[j])

    adj = [{j for j in range(n) if j != i and d[i][j] <= ADJACENT_DEG} for i in range(n)]
    order = sorted(range(n), key=lambda i: -len(adj[i]))    # 制約の厳しい種から先に置く

    color_of = {}
    forced = []
    for i in order:
        used = {color_of[j] for j in adj[i] if j in color_of}
        free = [c for c in range(len(PALETTE)) if c not in used]
        if free:
            # 空いている色のうち、同色の種が最も遠くなるものを選ぶ
            def far(c):
                same = [j for j, cc in color_of.items() if cc == c]
                return min((d[i][j] for j in same), default=999)
            color_of[i] = max(free, key=far)
        else:
            def far2(c):
                same = [j for j, cc in color_of.items() if cc == c]
                return min((d[i][j] for j in same), default=999)
            best = max(range(len(PALETTE)), key=far2)
            color_of[i] = best
            forced.append((i, far2(best)))

    for i, s in enumerate(species):
        s["color"] = PALETTE[color_of[i]]
        s["color_idx"] = color_of[i]

    # 検算: 同色ペアの最小距離
    worst = None
    for i in range(n):
        for j in range(i + 1, n):
            if color_of[i] == color_of[j]:
                if worst is None or d[i][j] < worst[0]:
                    worst = (d[i][j], species[i]["ja"], species[j]["ja"])
    return {"forced": forced, "worst": worst, "adj_max": max(len(a) for a in adj)}
