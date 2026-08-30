# -*- coding: utf-8 -*-
"""確認済みの点（data/verified/）から points.json と photos を作る。

sample_points.py が作る「表示用の点」と違い、こちらは
**1点1点が実際の車載写真で確認された点**。
点ごとに写真が付くので、詳細パネルで「その地点の写真」を出せる。

サンプリング版と入れ替えるのではなく併存させる:
  - 確認済みの点が十分に集まるまでは、地図がスカスカになってしまう
  - どちらの点かは見た目で区別できるようにする（build_atlas 側）
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402
from species import SPECIES  # noqa: E402
from verify_points import VERIFIED, load_state  # noqa: E402

OUT = DATA / "verified_points.json"


def main():
    out, total = {}, 0
    for s in SPECIES:
        sid = s["id"]
        if not (VERIFIED / f"{sid}.json").exists():
            continue
        st = load_state(sid)
        # CC BY-SA なので**撮影者の表示が要る**。
        # 画像を出す以上、帰属は削れない（ライセンス条件）。
        pts = [{"lat": a["lat"], "lon": a["lon"], "img": a["img_id"],
                "by": a.get("creator", ""), "at": a.get("captured_at")}
               for a in st["accepted"]]
        if pts:
            out[sid] = pts
            total += len(pts)
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"確認済み {total} 点 / {len(out)} 種 → {OUT}")
    if total == 0:
        print("（まだ0件。verify_points.py → review_ui.py を回す）")


if __name__ == "__main__":
    main()
