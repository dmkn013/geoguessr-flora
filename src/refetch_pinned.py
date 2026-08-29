# -*- coding: utf-8 -*-
"""PINNED のファイル名を直に取りに行く。無ければその種名で近いものを探す。"""
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_wikipedia import META, INTERVAL  # noqa: E402
from refetch_wikipedia import commons_thumb, try_save  # noqa: E402
from pinned_files import PINNED  # noqa: E402


def main():
    targets = sys.argv[1:] or list(PINNED)
    meta = json.loads(META.read_text(encoding="utf-8"))
    for sid in targets:
        done = False
        for fname in PINNED[sid]:
            title = "File:" + fname
            try:
                time.sleep(INTERVAL)
                t = commons_thumb(title)
                if not t:
                    print(f"  {sid}: '{fname}' 無し")
                    continue
                time.sleep(INTERVAL)
                meta[sid] = try_save(sid, t, "Wikimedia Commons", fname)
                print(f"{sid}: → {fname}")
                done = True
                break
            except Exception as e:
                print(f"  {sid} '{fname}': {e}")
        if not done:
            print(f"{sid}: **取れず**")
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
