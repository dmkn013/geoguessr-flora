# -*- coding: utf-8 -*-
"""ランダムな候補地点を引いて、実際の車載写真にその植物が写っているかで採否を決める。

    候補をランダムに引く → その地点の Mapillary 写真を取る
      → その植物が写っている？ → 写っていれば点を残す / 写っていなければ捨てて次へ

これが本来の設計。分布域からのサンプリング（sample_points.py）は
「分布の濃さの表示」でしかなく、個々の点に裏付けが無かった。
こちらは**1点1点が実際の写真で確認された点**になる。

判定は自動ではできない（種の同定は画像認識では信用できない）。
このスクリプトは**候補の写真を集めてコンタクトシートを作るところまで**をやり、
採否は人が review_ui.py の画面で目視して決める。
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
from paths import CANDIDATES, DATA  # noqa: E402
from land import load_land, on_land  # noqa: E402
from ranges import RANGES  # noqa: E402
from species import SPECIES  # noqa: E402

# 候補写真はローカルディスク（OneDrive同期外）。paths.py 参照。
CAND = CANDIDATES
VERIFIED = DATA / "verified"        # 判定結果
VERIFIED.mkdir(exist_ok=True)

# 1種あたり何枚の候補写真を集めるか。
# 判定で多くが落ちる（ユーカリは8枚中2枚）ので、多めに集めておく。
TARGET_PER_SPECIES = 40

# 1周でこの回数だけ候補を引く。打ち切りではなく**1周の区切り**で、
# 全種を1周したらまた最初の種に戻って足りない分を足す（round-robin）。
# 特定の種で延々と粘って他の種が始まらない、という事態を避けるため。
TRIES_PER_ROUND = 60


def weighted_pick(rngs, rnd):
    tot = sum(r[4] for r in rngs)
    x = rnd.random() * tot
    for i, r in enumerate(rngs):
        x -= r[4]
        if x <= 0:
            return i, r
    return len(rngs) - 1, rngs[-1]


def random_candidate(sid, rnd, land):
    """分布域の中からランダムに1点引く。陸地に載るまで引き直す。

    **どの矩形から引いたか（ri）も返す。**
    「ユーカリは豪州東部では高頻度だがポルトガルでは低頻度」のように、
    同じ種でも地域で遭遇率が違う。後から座標だけでは復元しにくいので
    引いた時点で記録しておく。
    """
    for _ in range(200):
        ri, (la0, la1, lo0, lo1, _w) = weighted_pick(RANGES[sid], rnd)
        la = rnd.uniform(la0, la1)
        lo = rnd.uniform(lo0, lo1)
        if on_land(lo, la, land):
            return round(la, 4), round(lo, 4), ri
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


def collect(sid, rnd, land, want, tries_budget):
    """候補を引いて写真を集める。判定はまだしない。

    1周ぶんの試行だけ回して戻る。足りなければ次の周でまた呼ばれる。
    既に見た座標は state に残るので、周をまたいでも重複しない。
    """
    st = load_state(sid)
    pend_path = CAND / sid / "_pending.json"
    (CAND / sid).mkdir(parents=True, exist_ok=True)
    pending = json.loads(pend_path.read_text(encoding="utf-8")) if pend_path.exists() else []

    have = len(st["accepted"]) + len(st["rejected"])
    seen = {tuple(a["pt"]) for a in st["accepted"]}
    seen |= {tuple(r["pt"]) for r in st["rejected"]}
    seen |= {(p[0], p[1]) for p in st["no_imagery"]}
    seen |= {tuple(p["pt"]) for p in pending}

    got = 0
    tries = 0
    while len(pending) + have < want and tries < tries_budget:
        tries += 1
        cand = random_candidate(sid, rnd, land)
        if not cand:
            continue
        c, ri = (cand[0], cand[1]), cand[2]
        if c in seen:
            continue
        seen.add(c)
        try:
            imgs = mapillary.images_around(c[0], c[1])
        except (mapillary.NoToken, mapillary.BadToken):
            raise
        except Exception as e:
            # 通信層で再試行済み。ここまで来たら記録して次へ
            print(f"    {c} 取得失敗: {type(e).__name__}", flush=True)
            continue
        if not imgs:
            st["no_imagery"].append([c[0], c[1], ri])
            if len(st["no_imagery"]) % 20 == 0:
                save_state(sid, st)
            continue
        img = imgs[0]
        url = img.get("thumb_1024_url")
        if not url:
            st["no_imagery"].append([c[0], c[1], ri])
            continue
        try:
            body = mapillary.fetch_thumb(url)
        except Exception as e:
            print(f"    {c} 画像失敗: {type(e).__name__}", flush=True)
            continue
        f = CAND / sid / f"{img['id']}.jpg"
        f.write_bytes(body)
        g = (img.get("computed_geometry") or {}).get("coordinates") or [c[1], c[0]]
        pending.append({"pt": list(c), "ri": ri, "img_id": img["id"], "file": f.name,
                        "lon": g[0], "lat": g[1],
                        "captured_at": img.get("captured_at"),
                        "creator": (img.get("creator") or {}).get("username", "")})
        got += 1
        print(f"    {len(pending) + have}/{want}: {c} → {f.name}", flush=True)
        # 長時間走らせるので、落ちても失わないよう都度書き出す
        save_state(sid, st)
        pend_path.write_text(json.dumps(pending, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    save_state(sid, st)
    pend_path.write_text(json.dumps(pending, ensure_ascii=False, indent=1), encoding="utf-8")
    return got, len(pending) + have


def main():
    targets = sys.argv[1:] or [s["id"] for s in SPECIES]
    targets = [t for t in targets if t in RANGES]
    try:
        mapillary.token()
    except mapillary.NoToken as e:
        print(e)
        return 1
    land = load_land()
    # 固定シードだと**再開のたびに同じ座標列を引き直す**。
    # 既出は seen で弾かれるので実害は無いが、試行回数を使い切って
    # 1枚も進まなくなる。長時間・複数回に分けて回す前提なので毎回変える。
    rnd = random.Random()

    # round-robin で全種を回る。1種で粘り続けて他が始まらないのを防ぐ。
    # 「もう新しい候補が出ない」種は done に入れて以後飛ばす。
    done = set()
    rnd_no = 0
    while len(done) < len(targets):
        rnd_no += 1
        print(f"\n===== 第{rnd_no}周 （完了 {len(done)}/{len(targets)} 種） =====",
              flush=True)
        for sid in targets:
            if sid in done:
                continue
            try:
                got, have = collect(sid, rnd, land, TARGET_PER_SPECIES, TRIES_PER_ROUND)
            except mapillary.BadToken as e:
                print(e)
                return 1
            print(f"[{sid}] +{got} → {have}/{TARGET_PER_SPECIES}", flush=True)
            if have >= TARGET_PER_SPECIES:
                done.add(sid)
                print(f"[{sid}] 目標到達", flush=True)
            elif got == 0:
                # この周で1枚も増えなかった＝カバレッジが薄い。
                # すぐ諦めず、周を重ねて別の乱数位置を試す。
                st = load_state(sid)
                tried = len(st["no_imagery"]) + len(st["accepted"]) + len(st["rejected"])
                if tried > 3000:
                    done.add(sid)
                    print(f"[{sid}] {tried}点試して打ち止め（Mapillaryの被覆が薄い）",
                          flush=True)

    print("\n収集終了。review_ui.py で判定する。", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
