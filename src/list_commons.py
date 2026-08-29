# -*- coding: utf-8 -*-
"""Commons のカテゴリの中身を列挙する。差し替え候補を選ぶための道具。

これが要る理由: ファイル名を推測して直指定したら**8種すべて存在しない名前**で失敗した。
検索の関連度も低い（オリーブで検索してカリフォルニアのブドウ園が1位になった）。
**列挙して、実在するものから選ぶ**のが結局いちばん速い。

    python src/list_commons.py "Olea europaea" "Acer saccharum"
"""
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_wikipedia import INTERVAL  # noqa: E402
from refetch_wikipedia import commons_images  # noqa: E402

for cat in sys.argv[1:]:
    print(f"### {cat}")
    try:
        time.sleep(INTERVAL)
        names = commons_images(cat, limit=30)
    except Exception as e:
        print("  取得失敗:", e)
        continue
    if not names:
        print("  （空 — カテゴリ名が違う可能性）")
    for n in names:
        print("   ", n)
