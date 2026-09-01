# -*- coding: utf-8 -*-
"""世界中からランダムに地点を引き、車載写真を集める。

これまでの収集（verify_points.py）と発想が逆:
  従来 = 種を決めて → その分布域を引く → その種が写っているか確認
  今回 = **世界中からランダムに引く** → 写っているものを全部タグ付け

従来方式は48種に限定されるので、画面に写っていた他の植物を全部捨てていた。
ランダムに引けば**実際の遭遇頻度がそのまま出る**し、48種の外側も拾える。

## 高速化（実測に基づく）

計測すると1地点3.82秒のうち **sleepは15%だけで、85%は通信の往復待ち**
だった。だから礼儀の待ち時間を削っても速くならない。3方向で手を入れた:

  A. 多段検索の廃止
     狭い→中→広と最大3回叩いていたのを、いきなり最大半径で1回に。
     **API呼び出しが1/3に減る**（負荷は下がる）。実測 3.82→2.82秒/地点。

  B. 並列化（WORKERS スレッド）
     待ち時間を重ねる。sleepは各スレッドで維持するので、
     単位時間あたりの負荷は WORKERS 倍だが、レート制限
     （検索API 10,000回/分）に対しては十分低い。実測 5.4倍。

  C. まとめ取り（1地点から PER_POINT 枚）
     同じ呼び出しで複数枚返ってくるのに1枚しか使っていなかった。
     **API負荷は変わらず**、1枚あたりのコストだけ下がる。

  ただし C は取りすぎると「同じ道路の連続写真」ばかりになり
  地理的多様性が落ちる。5枚に絞って必要地点数を確保する。

サンプリングの範囲:
  GeoGuessr の被覆に合わせる（＝Mapillary に写真がある地域）。
  写真が無い地域を引いても空振りするだけなので、結果的に被覆へ寄る。

再開可能: 引いた座標は state に残るので、止めても続きから。
"""
import json
import math
import random
import sys
import threading
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
WORKERS = 4            # 案B。上げすぎるとAPIに負荷をかけるので4で止める
PER_POINT = 5          # 案C。1地点から取る枚数。多様性とのトレードオフ
RADIUS = 0.049         # 案A。面積上限ぎりぎりの単一半径

LAT_MIN, LAT_MAX = -56.0, 72.0   # 極地は道路がほぼ無いので除く

lock = threading.Lock()


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"tried": 0, "seen": []}


def load_index():
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []


def random_land_point(rnd, land):
    """陸地上の点を1つ。緯度は sin 一様にして球面上で面積一様にする。"""
    for _ in range(400):
        lo = rnd.uniform(-180.0, 180.0)
        s = rnd.uniform(math.sin(math.radians(LAT_MIN)),
                        math.sin(math.radians(LAT_MAX)))
        la = math.degrees(math.asin(s))
        if on_land(lo, la, land):
            return round(la, 4), round(lo, 4)
    return None


class Shared:
    """スレッド間で共有する状態。書き込みは必ず lock 越しに。"""

    def __init__(self, st, idx):
        self.tried = st["tried"]
        self.seen = {tuple(p) for p in st["seen"]}
        self.idx = idx
        self.have = {it["img_id"] for it in idx}
        self.stop = False

    def count(self):
        return len(self.idx)

    def save(self):
        STATE.write_text(json.dumps(
            {"tried": self.tried, "seen": [list(p) for p in self.seen]},
            ensure_ascii=False), encoding="utf-8")
        INDEX.write_text(json.dumps(self.idx, ensure_ascii=False, indent=1),
                         encoding="utf-8")


def worker(wid, sh, land):
    rnd = random.Random()
    while not sh.stop:
        with lock:
            if sh.count() >= TARGET:
                sh.stop = True
                return
        c = random_land_point(rnd, land)
        if not c:
            continue
        with lock:
            if c in sh.seen:
                continue
            sh.seen.add(c)
            sh.tried += 1
        try:
            # 案A: 多段をやめて最大半径1回。案C: まとめて取る
            imgs = mapillary.images_near(c[0], c[1], radius_deg=RADIUS,
                                         limit=PER_POINT)
        except (mapillary.NoToken, mapillary.BadToken):
            sh.stop = True
            raise
        except Exception:
            continue
        if not imgs:
            continue
        for img in imgs:
            url = img.get("thumb_1024_url")
            if not url:
                continue
            with lock:
                if img["id"] in sh.have or sh.count() >= TARGET:
                    continue
                sh.have.add(img["id"])
            try:
                body = mapillary.fetch_thumb(url)
            except Exception:
                with lock:
                    sh.have.discard(img["id"])
                continue
            f = OUT / f"{img['id']}.jpg"
            f.write_bytes(body)
            g = (img.get("computed_geometry") or {}).get("coordinates") or [c[1], c[0]]
            with lock:
                sh.idx.append({"img_id": img["id"], "file": f.name,
                               "lat": g[1], "lon": g[0],
                               "captured_at": img.get("captured_at"),
                               "creator": (img.get("creator") or {}).get("username", "")})
                n = sh.count()
                if n % 25 == 0:
                    sh.save()
                    print(f"[{n}/{TARGET}] 引いた{sh.tried}地点 "
                          f"（1地点あたり{n/max(1,sh.tried):.1f}枚）", flush=True)


def main():
    try:
        mapillary.token()
    except mapillary.NoToken as e:
        print(e)
        return 1

    land = load_land()
    sh = Shared(load_state(), load_index())
    print(f"開始: 取得済み {sh.count()}/{TARGET}（引いた地点 {sh.tried}）"
          f" / {WORKERS}並列 × 1地点{PER_POINT}枚", flush=True)

    ths = [threading.Thread(target=worker, args=(i, sh, land), daemon=True)
           for i in range(WORKERS)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()

    sh.save()
    print(f"\n完了: {sh.count()}枚 / 引いた地点 {sh.tried}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
