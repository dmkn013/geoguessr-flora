# -*- coding: utf-8 -*-
"""タグ分布アトラス用のサムネイルを、タグごとの JSON に分けて書き出す。

なぜ分けるか:
  2,973枚を1ファイルに埋めると 15MB になり、モバイル回線で初回表示が重い。
  タグを選んだときにその分だけ取りに行けば、マツ属（685枚）でも 2MB 程度。

なぜ Mapillary の CDN を直接使わないか:
  thumb_*_url は**署名付きで期限が切れる**（実際に確認した）。
  埋め込んでも数日で画像が出なくなるので、自前で持つしかない。
"""
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CANDIDATES, DATA, DIST  # noqa: E402

SRC = CANDIDATES.parent / "random"
OUT = DIST / "thumbs"
SIZE = 200        # 詳細パネルで見る想定。160だと植物の形が潰れる
QUALITY = 58


def slug(name, i):
    """ファイル名にできない文字があるので通し番号で持つ。"""
    return f"t{i:02d}"


def main():
    tags = json.loads((DATA / "tags.json").read_text(encoding="utf-8"))
    idx = {x["img_id"]: x for x in
           json.loads((DATA / "random_index.json").read_text(encoding="utf-8"))}

    by_tag = {}
    for img_id, names in tags.items():
        for n in names:
            by_tag.setdefault(n, []).append(img_id)

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for i, (name, ids) in enumerate(sorted(by_tag.items(), key=lambda x: -len(x[1]))):
        shots = {}
        for img_id in ids:
            it = idx.get(img_id)
            if not it:
                continue
            f = SRC / it["file"]
            if not f.exists():
                continue
            im = Image.open(f).convert("RGB")
            if im.width / im.height > 1.9:      # 全天球は中央だけ
                cw = int(im.height * 1.6)
                im = im.crop(((im.width - cw) // 2, 0,
                              (im.width + cw) // 2, im.height))
            im.thumbnail((SIZE, SIZE), Image.LANCZOS)
            b = io.BytesIO()
            im.save(b, "JPEG", quality=QUALITY, optimize=True)
            shots[img_id] = base64.b64encode(b.getvalue()).decode()
        if not shots:
            continue
        key = slug(name, i)
        p = OUT / f"{key}.json"
        p.write_text(json.dumps(shots, separators=(",", ":")), encoding="utf-8")
        manifest[name] = key
        print(f"  {name:16s} {len(shots):4d}枚  {p.stat().st_size/1048576:5.2f} MB",
              flush=True)

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    tot = sum(f.stat().st_size for f in OUT.glob("*.json")) / 1048576
    print(f"\n{len(manifest)}タグ / 合計 {tot:.1f} MB → {OUT}")


if __name__ == "__main__":
    main()
