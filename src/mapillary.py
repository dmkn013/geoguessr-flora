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


def images_near(lat, lon, radius_deg=0.05, limit=8, fields=None):
    """点の周りの画像を探す。radius_deg は緯度経度の度数（0.05度≒5.5km）。

    完全に同じ座標に画像があることは期待できないので、
    「その点の近くで撮られた車載写真」を取りに行く。
    """
    f = fields or "id,computed_geometry,thumb_1024_url,captured_at,creator"
    bbox = f"{lon - radius_deg},{lat - radius_deg},{lon + radius_deg},{lat + radius_deg}"
    time.sleep(INTERVAL)
    d = _get("images", {"fields": f, "bbox": bbox, "limit": str(limit)})
    return d.get("data", [])


def fetch_thumb(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ctype = r.headers.get("Content-Type", "")
        body = r.read()
    if not ctype.startswith("image/"):
        raise RuntimeError(f"画像ではない応答: {ctype}")
    return body
