# -*- coding: utf-8 -*-
"""GeoGuessr のカバー国それぞれで、植物が写った点を最低30地点集める。

collect_random.py（世界一様ランダム）との違い:
  ランダムに引くと、国土の広い国ばかり当たって小国が埋まらない。
  実際 10,001 枚を引いた結果、カバー87カ国のうち73カ国が
  「植物ありの点」30未満だった（韓国1、イギリス6、日本18…）。
  ここでは**国ごとに目標を持って引く**。

やること:
  1. 対象国の国境ポリゴン内にランダムな点を打つ
  2. Mapillary に写真があれば取得
  3. 目標枚数に達したら次の国へ

タグ付けは tag_sheet.py が続きを拾う（random_index.json に足す）。

    python src/collect_country.py            # 不足している国を順に
    python src/collect_country.py 日本 韓国   # 国を指定
"""
import json
import random
import sys
import threading
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import mapillary  # noqa: E402
from coverage import COVERED, ja  # noqa: E402
from countries import _inside, load as load_countries  # noqa: E402
from paths import CANDIDATES, DATA  # noqa: E402

OUT = CANDIDATES.parent / "random"
INDEX = DATA / "random_index.json"
TAGS = DATA / "tags.json"
WHERE = DATA / "country_of.json"

TARGET_HIT = 30        # 各国で「植物あり」をこれだけ確保したい
HIT_RATE = 0.30        # 実測の植物あり率。必要枚数の見積もりに使う
WORKERS = 4
PER_POINT = 5
RADIUS = 0.049

lock = threading.Lock()


def load(p, d):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d


def polys_of(name):
    return [(x0, y0, x1, y1, poly)
            for n, x0, y0, x1, y1, poly in load_countries() if n == name]


def random_in(polys, rnd):
    """国境ポリゴン内の点。外接矩形で当てて内外判定で絞る。"""
    for _ in range(600):
        x0, y0, x1, y1, poly = rnd.choice(polys)
        lo = rnd.uniform(x0, x1)
        la = rnd.uniform(y0, y1)
        if _inside(lo, la, poly[0]) and not any(_inside(lo, la, h)
                                                for h in poly[1:]):
            return round(la, 4), round(lo, 4)
    return None


def shortfall():
    """国ごとに、あと何枚「植物あり」が要るか。"""
    tags = load(TAGS, {})
    where = load(WHERE, {})
    hit = Counter()
    for i, c in where.items():
        if c and tags.get(i):
            hit[c] += 1
    return {c: TARGET_HIT - hit[c] for c in COVERED if hit[c] < TARGET_HIT}


class Shared:
    def __init__(self, idx):
        self.idx = idx
        self.have = {it["img_id"] for it in idx}
        self.got = 0
        self.tried = 0
        self.stop = False

    def save(self):
        INDEX.write_text(json.dumps(self.idx, ensure_ascii=False, indent=1),
                         encoding="utf-8")


def worker(sh, polys, need, country):
    rnd = random.Random()
    while not sh.stop:
        with lock:
            if sh.got >= need:
                sh.stop = True
                return
            sh.tried += 1
            tried = sh.tried
        if tried > need * 40:            # 写真が無い国で無限に回らない
            sh.stop = True
            return
        c = random_in(polys, rnd)
        if not c:
            continue
        try:
            imgs = mapillary.images_near(c[0], c[1], radius_deg=RADIUS,
                                         limit=PER_POINT)
        except (mapillary.NoToken, mapillary.BadToken):
            sh.stop = True
            raise
        except Exception:
            continue
        for img in imgs or []:
            url = img.get("thumb_1024_url")
            if not url:
                continue
            with lock:
                if img["id"] in sh.have or sh.got >= need:
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
            g = (img.get("computed_geometry") or {}).get("coordinates") \
                or [c[1], c[0]]
            with lock:
                sh.idx.append({"img_id": img["id"], "file": f.name,
                               "lat": g[1], "lon": g[0],
                               "captured_at": img.get("captured_at"),
                               "creator": (img.get("creator") or {})
                               .get("username", ""),
                               "country": country})
                sh.got += 1
                if sh.got % 25 == 0:
                    sh.save()
                    print(f"    {sh.got}/{need}（{sh.tried}地点）", flush=True)


def collect(country, need_hit):
    polys = polys_of(country)
    if not polys:
        print(f"  {ja(country)}: 国境データなし。飛ばす")
        return 0
    need = int(need_hit / HIT_RATE) + 5      # 植物あり率から逆算
    print(f"{ja(country)}: 植物あり{need_hit}枚ぶん → {need}枚収集", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    sh = Shared(load(INDEX, []))
    ths = [threading.Thread(target=worker,
                            args=(sh, polys, need, country), daemon=True)
           for _ in range(WORKERS)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    sh.save()
    print(f"  → {sh.got}枚（{sh.tried}地点を試行）", flush=True)
    return sh.got


def main():
    try:
        mapillary.token()
    except mapillary.NoToken as e:
        print(e)
        return 1

    args = sys.argv[1:]
    need = shortfall()
    if args:
        ja2ne = {ja(c): c for c in COVERED}
        want = [ja2ne.get(a, a) for a in args]
        need = {c: need.get(c, TARGET_HIT) for c in want}

    # 不足の大きい順。埋まらない国で時間を使い切らないよう
    # 少ない国から片付ける手もあるが、まず穴の大きい方から。
    order = sorted(need.items(), key=lambda x: -x[1])
    print(f"対象 {len(order)}カ国 / 追加が必要な植物あり点 {sum(need.values())}\n")
    total = 0
    for c, n in order:
        total += collect(c, n)
    print(f"\n完了: {total}枚を追加")
    return 0


if __name__ == "__main__":
    sys.exit(main())
