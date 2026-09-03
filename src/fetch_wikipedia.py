# -*- coding: utf-8 -*-
"""Wikipedia から種ごとの代表画像を取り、data/photos_raw/ に生で置く。

方針:
  - 認証不要の `prop=pageimages` を使う（前回検証済み）。
  - **1.5秒間隔＋連絡先入り User-Agent**。Wikimedia のポリシー要件で、
    連続で叩くと Too many requests が HTML で返り、壊れた JPEG として保存される
    （前回これで PIL が落ちた）。
  - 取得したら**必ず中身を検証する**。Content-Type と PIL の両方で確かめ、
    HTMLエラーページを画像として保存しない。
  - 一度取れたものは再取得しない。目視確認して差し替える作業を
    何度も回すので、毎回APIを叩くとレート制限に当たる。

このスクリプトは「素材を集める」だけ。採用可否の目視確認は
review_photos.py が担当し、埋め込みは embed_photos.py が担当する。
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402
from species import SPECIES  # noqa: E402
from wiki_queries import QUERIES  # noqa: E402

RAW = DATA / "photos_raw"
RAW.mkdir(exist_ok=True)
META = DATA / "photos_raw" / "_meta.json"

# ポリシー要件: 連絡先を含む User-Agent。匿名の UA は弾かれる。
UA = "geoguessr-flora/0.1 (+https://github.com/dmkn013/geoguessr-flora) python-urllib"
INTERVAL = 1.5
API = "https://en.wikipedia.org/w/api.php"
THUMB_PX = 800


def get_json(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        ctype = r.headers.get("Content-Type", "")
        body = r.read()
    if "json" not in ctype:
        # レート制限のとき HTML が返る。JSONとして読まず、はっきり失敗させる。
        raise RuntimeError(f"JSONではない応答 ({ctype}) — レート制限の可能性")
    return json.loads(body.decode("utf-8"))


def get_binary(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ctype = r.headers.get("Content-Type", "")
        body = r.read()
    if not ctype.startswith("image/"):
        raise RuntimeError(f"画像ではない応答 ({ctype}) — レート制限の可能性")
    # PIL でも開けることを確かめる。ここを省くと壊れた画像が後段まで生き残る。
    Image.open(BytesIO(body)).verify()
    return body, ctype


def page_image(title):
    """記事の代表画像URLと、帰属表示に要る情報を返す。"""
    d = get_json({
        "action": "query", "format": "json", "formatversion": "2",
        "prop": "pageimages", "piprop": "thumbnail|original|name",
        "pithumbsize": str(THUMB_PX), "titles": title, "redirects": "1",
    })
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    p = pages[0]
    thumb = p.get("thumbnail")
    if not thumb:
        return None
    return {"title": p.get("title", title), "src": thumb["source"],
            "file": p.get("pageimage", "")}


def main():
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    todo = [s for s in SPECIES if s["id"] not in meta]
    print(f"対象 {len(todo)} 種（取得済み {len(meta)} 種はスキップ）")

    for i, s in enumerate(todo, 1):
        sid = s["id"]
        got = None
        for title in QUERIES[sid]:
            try:
                time.sleep(INTERVAL)
                info = page_image(title)
                if not info:
                    print(f"  [{sid}] '{title}' に代表画像なし → 次の候補")
                    continue
                time.sleep(INTERVAL)
                body, ctype = get_binary(info["src"])
            except Exception as e:
                print(f"  [{sid}] '{title}' 失敗: {e}")
                continue
            ext = ".jpg" if "jpeg" in ctype else ("." + ctype.split("/")[-1].split(";")[0])
            path = RAW / f"{sid}{ext}"
            path.write_bytes(body)
            w, h = Image.open(path).size
            got = {"id": sid, "article": info["title"], "file": info["file"],
                   "src_url": info["src"], "path": path.name, "w": w, "h": h}
            print(f"[{i}/{len(todo)}] {sid}: {info['title']} → {path.name} ({w}x{h})")
            break
        if got:
            meta[sid] = got
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            print(f"[{i}/{len(todo)}] {sid}: **取得できず**")

    missing = [s["id"] for s in SPECIES if s["id"] not in meta]
    print(f"\n取得済み {len(meta)}/{len(SPECIES)} 種")
    if missing:
        print("未取得:", ", ".join(missing))


if __name__ == "__main__":
    main()
