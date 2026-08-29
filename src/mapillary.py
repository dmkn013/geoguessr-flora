# -*- coding: utf-8 -*-
"""Mapillary API の薄いラッパ。

トークンは環境変数 MAPILLARY_TOKEN か data/.mapillary_token から読む。
**トークンはリポジトリに入れない**（.gitignore 済み）。

なぜ Mapillary か: CC-BY-SA で保存・再配布ができる。
Google Street View は規約が取得画像の保存・再配布を制限しており、
Artifact やリポジトリに埋め込むと再配布に当たる。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DATA  # noqa: E402

GRAPH = "https://graph.mapillary.com"
UA = "geoguessr-flora/0.2 (oyama51jdsf822qaf@gmail.com)"
INTERVAL = 0.2          # Mapillary は Wikimedia ほど厳しくないが礼儀として空ける
TOKEN_FILE = DATA / ".mapillary_token"


class NoToken(RuntimeError):
    pass


class BadToken(RuntimeError):
    """トークンが拒否された。候補を引き続けても無駄なので即止める。"""


def token():
    t = os.environ.get("MAPILLARY_TOKEN", "").strip()
    if not t and TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not t:
        raise NoToken(
            "Mapillary のトークンが無い。\n"
            "  https://www.mapillary.com/dashboard/developers で Register Application し、\n"
            f"  トークンを {TOKEN_FILE} に貼るか、環境変数 MAPILLARY_TOKEN に入れる。"
        )
    return t


def _get(path, params):
    q = dict(params)
    q["access_token"] = token()
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 認証エラーを「この地点には写真が無い」と取り違えると、
        # 全候補を空振りで消費してしまう。区別して即止める。
        if e.code in (400, 401, 403):
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            if "OAuth" in body or "Access Token" in body or e.code in (401, 403):
                raise BadToken(f"トークンが拒否された (HTTP {e.code}): {body}")
        raise


# bbox の面積上限は 0.010 平方度。半径 r 度なら (2r)^2 <= 0.010 なので r <= 0.05。
# 境界ちょうどは丸めで弾かれるため、少し内側を上限にする。
MAX_RADIUS_DEG = 0.049


def images_near(lat, lon, radius_deg=MAX_RADIUS_DEG, limit=8, fields=None):
    """点の周りの画像を探す。radius_deg は緯度経度の度数（0.049度≒5.4km）。

    完全に同じ座標に画像があることは期待できないので、
    「その点の近くで撮られた車載写真」を取りに行く。

    **面積上限に注意**: bbox が 0.010 平方度を超えると HTTP 500 が返る。
    これを「その地点に写真が無い」と誤読すると、実際には写真がある候補を
    捨ててしまう（最初それで豪州内陸の候補を軒並み落としていた）。
    """
    r = min(radius_deg, MAX_RADIUS_DEG)
    f = fields or "id,computed_geometry,thumb_1024_url,captured_at,creator"
    bbox = f"{lon - r},{lat - r},{lon + r},{lat + r}"
    time.sleep(INTERVAL)
    d = _get("images", {"fields": f, "bbox": bbox, "limit": str(limit)})
    return d.get("data", [])


def images_around(lat, lon, limit=8, radii=(0.005, 0.012, 0.049), retries=1):
    """近い順に広げて探す。近くにあればそれを使い、無ければ広げる。

    **500 を「写真が無い」と同一視して候補を捨てない**のが要点。
    最初それをやって豪州内陸の候補を軒並み落としていた（実際は bbox が
    面積上限 0.010 平方度を超えていただけだった）。

    ただし広い bbox は画像密度の高い地域で
    "Please reduce the amount of data" の 500 を返すことがあり、これは
    limit を下げても消えない（面積そのものが重いため）。
    その場合でも**狭い半径が 0 件を返していれば**、
    近傍に写真は無いと判断してよいので 0 件として扱う。
    """
    narrow_ok = False          # 狭い半径がエラー無しで走ったか
    for r in radii:
        for attempt in range(retries + 1):
            try:
                got = images_near(lat, lon, radius_deg=r, limit=limit)
            except BadToken:
                raise
            except urllib.error.HTTPError as e:
                if e.code == 500 and attempt < retries:
                    time.sleep(0.4)
                    continue
                if e.code == 500 and narrow_ok:
                    return []   # 狭い範囲は確認済みで0件。広い範囲が重いだけ
                if e.code != 500:
                    raise
                break
            if got:
                return got
            narrow_ok = True
            break
    return []
