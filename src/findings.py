# -*- coding: utf-8 -*-
"""収集・判定の途中で気づいた「候補になりそうな種・特徴」を書き留める。

数百枚の車載写真を見ていると、**狙っていない種**が繰り返し目に入る。
「この地域ではこれがよく写る」という気づきは、それ自体がメタになりうる。
その場で species.py に足すと教材の中身が検証されないまま増えるので、
いったんここに溜めて、後から人が採否を決める。

    python src/findings.py add --region "豪州南東部（VIC）" \
        --what "路肩の黄色い低木（アカシア類？）" --note "3枚で見た"
    python src/findings.py list
    python src/findings.py promote 3      # species.py 追加の下書きを出す

記録するのは「見た」という事実と、どの画像で見たか。
種の同定が曖昧でも書いてよい（「マメ科の黄色い花の低木」で十分）。
後から画像を見返せるよう、必ず出典の画像IDを残す。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402

OUT = DATA / "findings.json"


def load():
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []


def save(items):
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def add(args):
    """気づきを1件足す。"""
    d = {}
    key = None
    for a in args:
        if a.startswith("--"):
            key = a[2:]
            d[key] = ""
        elif key:
            d[key] = (d[key] + " " + a).strip()
    if not d.get("what"):
        print("--what は必須（何を見たか）")
        return
    items = load()
    d.setdefault("region", "")
    d.setdefault("note", "")
    d.setdefault("imgs", "")
    d.setdefault("seen", 1)
    d["id"] = (max((x["id"] for x in items), default=0) + 1)
    items.append(d)
    save(items)
    print(f"[{d['id']}] {d['region']} / {d['what']}")


def show():
    items = load()
    if not items:
        print("まだ何も無い。")
        print("  python src/findings.py add --region 地域 --what 見たもの --note メモ")
        return
    print(f"{'id':>3s}  {'地域':22s} 見たもの")
    for d in items:
        print(f"{d['id']:3d}  {d.get('region', ''):22s} {d['what']}")
        if d.get("note"):
            print(f"     └ {d['note']}")
        if d.get("imgs"):
            print(f"     └ 画像: {d['imgs']}")
    print(f"\n{len(items)}件。species.py に足す候補は promote で下書きを出す。")


def promote(fid):
    items = load()
    d = next((x for x in items if x["id"] == int(fid)), None)
    if not d:
        print(f"id {fid} が無い")
        return
    # id は ASCII の英数字だけ。日本語の説明からは作れないので、
    # 作れなければ空欄にして手で決めてもらう。
    sid = "".join(c for c in d["what"].lower() if c.isascii() and c.isalnum())[:14]
    sid = sid or "（id を決める）"
    print("# species.py に足す下書き。中身（tells / trap）は要検証。")
    print(f"""    dict(
        id="{sid}", ja="", en="", sci="",
        group="", color="",
        regions=["{d.get('region', '')}"],
        tells=["{d['what']}"],
        trap="",
    ),""")
    print(f"\n# ranges.py にも分布域の矩形が要る。")
    print(f"# 出典画像: {d.get('imgs', '(記録なし)')}")
    print(f"# メモ: {d.get('note', '')}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "add":
        add(sys.argv[2:])
    elif cmd == "list":
        show()
    elif cmd == "promote" and len(sys.argv) > 2:
        promote(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
