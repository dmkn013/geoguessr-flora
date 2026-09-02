# -*- coding: utf-8 -*-
"""タグの表記ゆれを正規化する。

複数のエージェントが自由にタグを作るので、同じものが違う名前で入る。
実際に出たゆれ:
  マツ科 / マツ属          → 科は粒度が粗すぎるので属に寄せる
  ハコヤナギ属 / ポプラ属   → どちらも Populus
  バナナ（属タグなし）      → 種名だけだと属レベルの集計から漏れる

種名タグには対応する属タグも補う（属レベルでも数えられるように）。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA  # noqa: E402

TAGS = DATA / "tags.json"

# 別名 → 正規名
ALIAS = {
    "マツ科": "マツ属",
    "ハコヤナギ属": "ポプラ属",
    # 同じものを別名で書いてくるケース（実際に出た）
    "ココヤシ属": "ココヤシ",
    "バナナ属": "バショウ属",
    "アメリカネムノキ": "ネムノキ属",
    "パンダナス属": "タコノキ属",
}

# 種名 → 補う属タグ
SPECIES_GENUS = {
    "バナナ": "バショウ属",
    "ココヤシ": "ヤシ科",
    "ヨーロッパアカマツ": "マツ属",
    "ベンガルボダイジュ": "イチジク属",
    "オウギヤシ": "オウギヤシ属",
}


def main():
    t = json.loads(TAGS.read_text(encoding="utf-8"))
    changed = 0
    for k, v in t.items():
        new = []
        for raw in v:
            # カンマ・読点で区切って入れてくる場合がある（実際に出た）
            for x in [y.strip() for y in raw.replace("、", ",").split(",") if y.strip()]:
                new.append(ALIAS.get(x, x))
                g = SPECIES_GENUS.get(x)
                if g:
                    new.append(g)
        new = list(dict.fromkeys(new))
        if new != v:
            changed += 1
            t[k] = new
    TAGS.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    c = Counter(x for v in t.values() for x in v)
    print(f"{changed}枚を正規化 / タグ {len(c)}種類")
    for name, n in c.most_common():
        print(f"  {name:20s}{n:4d}")


if __name__ == "__main__":
    main()
