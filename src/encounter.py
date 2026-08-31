# -*- coding: utf-8 -*-
"""遭遇率を出す。「その地域を引いたとき、画面にその植物が写っている確率」。

なぜ要るか:
  「ユーカリが見えたら豪州」は、豪州でユーカリが**実際によく見える**から
  役に立つ。もし分布はしていても道端でほとんど見ないなら、
  覚えても当たらない＝教材としての価値が低い。

  分布の有無（0/1）ではなく**頻度**を出すことで、
  「強いメタ」と「知識としては正しいが使えないメタ」を区別できる。

判定の内訳から出す:
    採用 / (採用 + 却下)         = 写真があった地点で実際に写っていた率
    (採用 + 却下) / 全候補       = そもそも写真がある率（Mapillaryの被覆）
    採用 / 全候補                = 総合的な遭遇率

これらは**標本から推定した値**なので、標本が少ないうちは大きく振れる。
だから件数も一緒に出し、少ない場合は「参考値」と分かるようにする。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402
from ranges import RANGES  # noqa: E402
from regions import region_of  # noqa: E402
from species import SPECIES  # noqa: E402
from verify_points import CAND, VERIFIED, load_state  # noqa: E402

OUT = DATA / "encounter.json"

# この件数を下回る地域は「参考値」扱いにする。
# 5件で1件採用なら20%だが、実際には5%かもしれないし50%かもしれない。
MIN_SAMPLES = 8


def wilson(k, n, z=1.96):
    """Wilson score 区間。少数標本でも破綻しない信頼区間。

    単純な k/n だと 0/3 が「0%」になってしまう。
    実際には「まだ分からない」であって「絶対に見えない」ではない。
    """
    if n == 0:
        return 0.0, 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - m), min(1.0, c + m)


def region_name(sid, ri, lat=None, lon=None):
    """地域名を引く。

    **実際の座標があればそれを使う**。矩形番号(ri)は途中から記録し始めた
    ので古い候補には無く、また矩形の中心と実際の点はずれることもある。
    座標そのものから引くほうが正確で、取りこぼしも無い。
    """
    if lat is not None and lon is not None:
        return region_of(lat, lon)
    rs = RANGES.get(sid) or []
    if ri is None or ri >= len(rs):
        return "不明"
    la0, la1, lo0, lo1, _w = rs[ri]
    return region_of((la0 + la1) / 2, (lo0 + lo1) / 2)


def stats_for(sid):
    st = load_state(sid)
    pend_path = CAND / sid / "_pending.json"
    pending = json.loads(pend_path.read_text(encoding="utf-8")) if pend_path.exists() else []

    # 地域ごとに集計
    by = {}

    def slot(ri, lat=None, lon=None):
        name = region_name(sid, ri, lat, lon)
        return by.setdefault(name, {"acc": 0, "rej": 0, "noimg": 0, "pend": 0})

    for a in st["accepted"]:
        slot(a.get("ri"), a.get("lat"), a.get("lon"))["acc"] += 1
    for r in st["rejected"]:
        slot(r.get("ri"), r.get("lat"), r.get("lon"))["rej"] += 1
    for p in st["no_imagery"]:
        # no_imagery は [lat, lon] か [lat, lon, ri]
        slot(p[2] if len(p) > 2 else None, p[0], p[1])["noimg"] += 1
    for p in pending:
        slot(p.get("ri"), p.get("lat"), p.get("lon"))["pend"] += 1

    regions = []
    for name, c in sorted(by.items(), key=lambda kv: -(kv[1]["acc"] + kv[1]["rej"])):
        judged = c["acc"] + c["rej"]
        tried = judged + c["noimg"]
        seen_p, seen_lo, seen_hi = wilson(c["acc"], judged)
        regions.append({
            "region": name,
            "accepted": c["acc"], "rejected": c["rej"],
            "no_imagery": c["noimg"], "pending": c["pend"],
            "judged": judged, "tried": tried,
            # 写真があった地点のうち、実際に写っていた率
            "seen_rate": round(seen_p, 3),
            "seen_lo": round(seen_lo, 3), "seen_hi": round(seen_hi, 3),
            # Mapillary に写真がある率（教材の価値とは別の、データ側の事情）
            "imagery_rate": round(judged / tried, 3) if tried else 0.0,
            "enough": judged >= MIN_SAMPLES,
        })

    t_acc = sum(r["accepted"] for r in regions)
    t_judged = sum(r["judged"] for r in regions)
    t_tried = sum(r["tried"] for r in regions)
    p, lo, hi = wilson(t_acc, t_judged)
    return {
        "accepted": t_acc, "judged": t_judged, "tried": t_tried,
        # 撮影データがある地点の割合。低い＝「その植物が稀」ではなく
        # 「Mapillary の被覆が薄い」。両者を混同しないため分けて出す。
        "imagery_rate": round(t_judged / t_tried, 3) if t_tried else 0.0,
        "seen_rate": round(p, 3), "seen_lo": round(lo, 3), "seen_hi": round(hi, 3),
        "enough": t_judged >= MIN_SAMPLES,
        "regions": regions,
    }


def main():
    out = {}
    for s in SPECIES:
        if not (VERIFIED / f"{s['id']}.json").exists():
            continue
        out[s["id"]] = stats_for(s["id"])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{'種':16s}{'判定':>6s}{'採用':>5s}  遭遇率")
    for s in SPECIES:
        d = out.get(s["id"])
        if not d or not d["judged"]:
            continue
        mark = "" if d["enough"] else "  ※標本少"
        print(f"{s['id']:16s}{d['judged']:6d}{d['accepted']:5d}  "
              f"{d['seen_rate']*100:4.0f}% "
              f"[{d['seen_lo']*100:.0f}–{d['seen_hi']*100:.0f}%]{mark}")
    print(f"\n保存: {OUT}")
    if not any(d["judged"] for d in out.values()):
        print("（まだ判定が0件。review_ui.py で判定すると数字が出る）")


if __name__ == "__main__":
    main()
