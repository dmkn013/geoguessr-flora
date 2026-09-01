# -*- coding: utf-8 -*-
"""世界中からランダムに地点を引き、車載写真を集める。

これまでの収集（verify_points.py）と発想が逆:
  従来 = 種を決めて → その分布域を引く → その種が写っているか確認
  今回 = **世界中からランダムに引く** → 写っているものを全部タグ付け

従来方式は48種に限定されるので、画面に写っていた他の植物を全部捨てていた。
ランダムに引けば**実際の遭遇頻度がそのまま出る**し、48種の外側も拾える。

サンプリングの範囲:
  GeoGuessr の被覆に合わせる（＝Mapillary に写真がある地域）。
  被覆国リストは公開ソースが取りにくいので、
  **写真が実際に取れるかどうか**で判断する（coverage_probe.py で実測）。
  写真が無い地域を引いても空振りするだけなので、結果的に被覆へ寄る。

再開可能: 引いた座標は全部 state に残るので、止めても続きから。
"""
import json
import random
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import mapillary  # noqa: E402
from land import load_land, on_land  # noqa: E402
from paths import CANDIDATES, DATA  # noqa: E402

OUT = CANDIDATES.parent / "random"
OUT.mkdir(parents=True, exist_ok=True)
STATE = DATA / "random_state.json"
INDEX = DATA / "random_index.json"

TARGET = 10000

# 極地は道路がほぼ無く空振りが増えるので緯度を絞る。
# GeoGuessr の出題もこの範囲にほぼ収まる。
LAT_MIN, LAT_MAX = -56.0, 72.0


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"tried": 0, "got": 0, "seen": []}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def load_index():
    if INDEX.exists():
        return json.loads(INDEX.read_text(encoding="utf-8"))
    return []


def save_index(idx):
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


def random_land_point(rnd, land):
    """陸地上の点をランダムに1つ。

    緯度は cos 補正して球面上で一様にする。補正しないと極地が過剰に出る。
    """
    import math
    for _ in range(400):
        lo = rnd.uniform(-180.0, 180.0)
        # 面積一様サンプリング: sin(lat) を一様に引く
        s = rnd.uniform(math.sin(math.radians(LAT_MIN)),
                        math.sin(math.radians(LAT_MAX)))
        la = math.degrees(math.asin(s))
        if on_land(lo, la, land):
            return round(la, 4), round(lo, 4)
    return None


def main():
    try:
        mapillary.token()
    except mapillary.NoToken as e:
        print(e)
        return 1

    land = load_land()
    rnd = random.Random()
    st = load_state()
    idx = load_index()
    seen = {tuple(p) for p in st["seen"]}
    got = len(idx)

    print(f"開始: 取得済み {got}/{TARGET}（引いた地点 {st['tried']}）", flush=True)

    while got < TARGET:
        c = random_land_point(rnd, land)
        if not c or c in seen:
            continue
        seen.add(c)
        st["tried"] += 1
        try:
            imgs = mapillary.images_around(c[0], c[1], limit=3)
        except (mapillary.NoToken, mapillary.BadToken):
            raise
        except Exception as e:
            print(f"  {c} 取得失敗 {type(e).__name__}", flush=True)
            continue
        if not imgs:
            if st["tried"] % 200 == 0:
                st["seen"] = [list(p) for p in seen]
                save_state(st)
                print(f"  … 引いた{st['tried']} 取得{got}", flush=True)
            continue
        img = imgs[0]
        url = img.get("thumb_1024_url")
        if not url:
            continue
        try:
            body = mapillary.fetch_thumb(url)
        except Exception as e:
            print(f"  {c} 画像失敗 {type(e).__name__}", flush=True)
            continue
        f = OUT / f"{img['id']}.jpg"
        f.write_bytes(body)
        g = (img.get("computed_geometry") or {}).get("coordinates") or [c[1], c[0]]
        idx.append({"img_id": img["id"], "file": f.name,
                    "lat": g[1], "lon": g[0],
                    "captured_at": img.get("captured_at"),
                    "creator": (img.get("creator") or {}).get("username", "")})
        got += 1
        if got % 10 == 0:
            st["seen"] = [list(p) for p in seen]
            st["got"] = got
            save_state(st)
            save_index(idx)
            print(f"[{got}/{TARGET}] 引いた{st['tried']} "
                  f"（ヒット率{got/st['tried']*100:.0f}%）", flush=True)

    st["seen"] = [list(p) for p in seen]
    st["got"] = got
    save_state(st)
    save_index(idx)
    print(f"\n完了: {got}枚 / 引いた地点 {st['tried']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
