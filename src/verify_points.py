# -*- coding: utf-8 -*-
"""ランダムな候補地点を引いて、実際の車載写真にその植物が写っているかで採否を決める。

    候補をランダムに引く → その地点の Mapillary 写真を取る
      → その植物が写っている？ → 写っていれば点を残す / 写っていなければ捨てて次へ

これが本来の設計。分布域からのサンプリング（sample_points.py）は
「分布の濃さの表示」でしかなく、個々の点に裏付けが無かった。
こちらは**1点1点が実際の写真で確認された点**になる。

判定は自動ではできない（種の同定は画像認識では信用できない）。
このスクリプトは**候補の写真を集めてコンタクトシートを作るところまで**をやり、
採否は人（またはレビュー担当）が review_candidates で目視して決める。
判定結果は data/verified/<種id>.json に追記される。

再開可能: 既に判定済みの候補は再取得しない。
"""
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import mapillary  # noqa: E402
from paths import DATA  # noqa: E402
from land import load_land, on_land  # noqa: E402
from ranges import RANGES  # noqa: E402
from species import SPECIES  # noqa: E402

CAND = DATA / "candidates"          # 候補の写真とメタ
VERIFIED = DATA / "verified"        # 判定結果
CAND.mkdir(exist_ok=True)
VERIFIED.mkdir(exist_ok=True)

# 1種あたり何点の「確認済み」を目指すか。
# 2,785点（表示用サンプリング）とは桁が違う。1点ずつ写真を見るので当然。
TARGET_PER_SPECIES = 8
MAX_TRIES_PER_POINT = 40    # 候補を引いて写真が無い/写っていないを何回まで試すか


def weighted_pick(rngs, rnd):
    tot = sum(r[4] for r in rngs)
    x = rnd.random() * tot
    for r in rngs:
        x -= r[4]
        if x <= 0:
            return r
    return rngs[-1]


def random_candidate(sid, rnd, land):
    """分布域の中からランダムに1点引く。陸地に載るまで引き直す。"""
    for _ in range(200):
        la0, la1, lo0, lo1, _w = weighted_pick(RANGES[sid], rnd)
        la = rnd.uniform(la0, la1)
        lo = rnd.uniform(lo0, lo1)
        if on_land(lo, la, land):
            return round(la, 4), round(lo, 4)
    return None


def state_path(sid):
    return VERIFIED / f"{sid}.json"


def load_state(sid):
    p = state_path(sid)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"accepted": [], "rejected": [], "no_imagery": []}


def save_state(sid, st):
    state_path(sid).write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def collect(sid, rnd, land, want):
    """候補を引いて写真を集める。判定はまだしない。"""
    st = load_state(sid)
    have = len(st["accepted"])
    seen = {tuple(a["pt"]) for a in st["accepted"]}
    seen |= {tuple(r["pt"]) for r in st["rejected"]}
    seen |= {tuple(p) for p in st["no_imagery"]}
    pending = []
    tries = 0
    while len(pending) + have < want and tries < MAX_TRIES_PER_POINT:
        tries += 1
        c = random_candidate(sid, rnd, land)
        if not c or c in seen:
            continue
        seen.add(c)
        try:
            imgs = mapillary.images_around(c[0], c[1])
        except (mapillary.NoToken, mapillary.BadToken):
            raise
        except Exception as e:
            print(f"    {c} 取得失敗: {e}")
            continue
        if not imgs:
            st["no_imagery"].append(list(c))
            continue
        img = imgs[0]
        url = img.get("thumb_1024_url")
        if not url:
            st["no_imagery"].append(list(c))
            continue
        try:
            body = mapillary.fetch_thumb(url)
        except Exception as e:
            print(f"    {c} 画像失敗: {e}")
            continue
        d = CAND / sid
        d.mkdir(exist_ok=True)
        f = d / f"{img['id']}.jpg"
        f.write_bytes(body)
        g = (img.get("computed_geometry") or {}).get("coordinates") or [c[1], c[0]]
        pending.append({"pt": list(c), "img_id": img["id"], "file": f.name,
                        "lon": g[0], "lat": g[1],
                        "captured_at": img.get("captured_at")})
        print(f"    候補 {len(pending)+have}/{want}: {c} → {f.name}")
    save_state(sid, st)
    (CAND / sid / "_pending.json").write_text(
        json.dumps(pending, ensure_ascii=False, indent=1), encoding="utf-8")
    return pending


def main():
    targets = sys.argv[1:] or [s["id"] for s in SPECIES]
    try:
        mapillary.token()
    except mapillary.NoToken as e:
        print(e)
        return 1
    land = load_land()
    rnd = random.Random(20260830)
    for sid in targets:
        if sid not in RANGES:
            print(f"{sid}: 分布域が未定義"); continue
        print(f"[{sid}]")
        try:
            collect(sid, rnd, land, TARGET_PER_SPECIES)
        except mapillary.BadToken as e:
            print(e)
            return 1
    print("\n候補の写真を集めた。review_candidates.py で目視して採否を決める。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
