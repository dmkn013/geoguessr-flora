# -*- coding: utf-8 -*-
"""目視で落とした種を、別の記事・別の探し方で取り直す。

1巡目の失敗はほぼ「記事の先頭画像＝植物図版か果実のクローズアップ」だった。
そこで2段構えにする:
  1. RETRY に書いた「栽培・景観寄りの記事」の代表画像を試す
  2. それでも駄目なら **Commons のカテゴリから実写を拾う**
     （カテゴリには生育地の写真が入っている。図版は Category:Botanical illustrations 側に寄る）

取り直した結果も必ず目視する。自動で"良くなったこと"にしない。
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_wikipedia import META, RAW, INTERVAL, UA, get_binary, page_image  # noqa: E402
from wiki_queries import RETRY  # noqa: E402

COMMONS = "https://commons.wikimedia.org/w/api.php"
THUMB = 800
# 図版・標本・地図・種子など、景観として使えないものを名前で弾く
BAD = ("illustration", "botanical", "plate", "herbarium", "specimen", "drawing",
       "map", "distribution", "seed", "fruit", "flower", "leaf ", "closeup",
       "close-up", "diagram", "logo", "koehler", "flora_de", "icones")


def commons_images(category, limit=12):
    """Commons のカテゴリから画像ファイル名を取る。"""
    url = COMMONS + "?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2",
        "list": "categorymembers", "cmtitle": f"Category:{category}",
        "cmtype": "file", "cmlimit": str(limit),
    })
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    return [m["title"] for m in d.get("query", {}).get("categorymembers", [])]


def commons_thumb(filetitle):
    url = COMMONS + "?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2",
        "prop": "imageinfo", "iiprop": "url", "iiurlwidth": str(THUMB),
        "titles": filetitle,
    })
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    pages = d.get("query", {}).get("pages", [])
    if not pages or "imageinfo" not in pages[0]:
        return None
    return pages[0]["imageinfo"][0].get("thumburl")


def try_save(sid, url, article, filename):
    body, ctype = get_binary(url)
    ext = ".jpg" if "jpeg" in ctype else ("." + ctype.split("/")[-1].split(";")[0])
    path = RAW / f"{sid}{ext}"
    path.write_bytes(body)
    w, h = Image.open(path).size
    return {"id": sid, "article": article, "file": filename,
            "src_url": url, "path": path.name, "w": w, "h": h}


def main():
    targets = sys.argv[1:] or list(RETRY)
    meta = json.loads(META.read_text(encoding="utf-8"))
    for sid in targets:
        done = False
        for title in RETRY.get(sid, []):
            try:
                time.sleep(INTERVAL)
                info = page_image(title)
                if not info:
                    continue
                time.sleep(INTERVAL)
                meta[sid] = try_save(sid, info["src"], info["title"], info["file"])
                print(f"{sid}: 記事 '{info['title']}' → {info['file']}")
                done = True
                break
            except Exception as e:
                print(f"  {sid} '{title}': {e}")
        if not done:
            # Commons カテゴリへフォールバック
            for cat in RETRY.get(sid, []):
                try:
                    time.sleep(INTERVAL)
                    names = commons_images(cat)
                except Exception as e:
                    print(f"  {sid} cat '{cat}': {e}")
                    continue
                for n in names:
                    low = n.lower()
                    if any(b in low for b in BAD):
                        continue
                    try:
                        time.sleep(INTERVAL)
                        t = commons_thumb(n)
                        if not t:
                            continue
                        time.sleep(INTERVAL)
                        meta[sid] = try_save(sid, t, f"Commons:{cat}", n.replace("File:", ""))
                        print(f"{sid}: Commons '{cat}' → {n}")
                        done = True
                        break
                    except Exception as e:
                        print(f"  {sid} {n}: {e}")
                if done:
                    break
        if not done:
            print(f"{sid}: **取り直せず**")
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
