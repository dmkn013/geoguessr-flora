# -*- coding: utf-8 -*-
"""リポジトリ内の場所をここに集約する。

src/ から見て ../data（入力と中間データ）と ../dist（成果物）を指す。
各スクリプトが個別に __file__ から組み立てると、移動のたびに壊れるため。

**候補写真だけは別扱い。**
このリポジトリは OneDrive 配下にあり、収集は数千枚の小さなファイルを
延々と書き続ける。同期対象に置くと OneDrive が回り続けるので、
CANDIDATES はローカルディスク（同期しない場所）に置く。
判定結果や出典IDは data/ 側に残るので、写真が消えても再取得できる。
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DIST = ROOT / "dist"

DATA.mkdir(exist_ok=True)
DIST.mkdir(exist_ok=True)


def _candidates_dir():
    """候補写真の置き場。環境変数 > ローカルwork > data配下 の順に決める。"""
    env = os.environ.get("FLORA_CANDIDATES", "").strip()
    if env:
        return Path(env)
    # OneDrive 配下なら、同期しないローカルへ逃がす
    if "OneDrive" in str(ROOT):
        local = Path.home() / "work" / "geoguessr-flora-data" / "candidates"
        try:
            local.mkdir(parents=True, exist_ok=True)
            return local
        except OSError:
            pass
    return DATA / "candidates"


CANDIDATES = _candidates_dir()
CANDIDATES.mkdir(parents=True, exist_ok=True)
