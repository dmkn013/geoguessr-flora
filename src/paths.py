# -*- coding: utf-8 -*-
"""リポジトリ内の場所をここに集約する。

src/ から見て ../data（入力と中間データ）と ../dist（成果物）を指す。
各スクリプトが個別に __file__ から組み立てると、移動のたびに壊れるため。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DIST = ROOT / "dist"

DATA.mkdir(exist_ok=True)
DIST.mkdir(exist_ok=True)
