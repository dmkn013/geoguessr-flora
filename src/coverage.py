# -*- coding: utf-8 -*-
"""GeoGuessr（＝Google Street View 公式車載）のカバー国。

出典: Wikipedia "Google Street View in Africa / Asia / Europe /
      North America / South America / Oceania"（2026年9月時点）

**フォトスフィア（利用者投稿の360度写真）だけの国は含めない。**
GeoGuessr の標準的な世界マップには出てこないので、
そこで見える植物を覚えても無駄になる（ユーザー判断）。

代表的な非カバー国:
  タンザニア、カザフスタン、マリ、パキスタン、ジョージア
    （Wikipedia は sparse/partial と書いているが、GeoGuessr の
     世界マップには出ない。ユーザー指摘で除外した）
  中国本土、ミャンマー、北朝鮮、イラン、アフガニスタン、イラク、
  シリア、サウジアラビア、リビア、アルジェリア、モロッコ、
  スーダン、ソマリア、エチオピア、コンゴ民主共和国、アンゴラ、
  モザンビーク、ザンビア、ジンバブエ、チャド、ニジェール、
  ブルキナファソ、ギニア、コートジボワール、カメルーン、
  ベリーズ、ホンジュラス、ニカラグア、キューバ、ジャマイカ、
  ハイチ、ベネズエラ、ガイアナ、スリナム、
  パプアニューギニア、フィジー、ソロモン諸島、ベラルーシ、
  アルメニア、アゼルバイジャン、ウズベキスタン、トルクメニスタン、
  タジキスタン、ブルネイ、東ティモール

キーは data/countries50m.json（Natural Earth 50m）の name。
110m だとマルタ・シンガポールが省略されていて点を打てなかった。

香港・マカオはカバー国だが 50m にも独立ポリゴンが無いので
扱えていない（中国本土の一部として落ちる）。
"""

# Natural Earth の name → 日本語名
COVERED = {
    # --- ヨーロッパ ---
    "Albania": "アルバニア", "Austria": "オーストリア",
    "Belgium": "ベルギー", "Bosnia and Herz.": "ボスニア・ヘルツェゴビナ",
    "Bulgaria": "ブルガリア", "Croatia": "クロアチア",
    "Cyprus": "キプロス", "Czechia": "チェコ", "Denmark": "デンマーク",
    "Estonia": "エストニア", "Finland": "フィンランド",
    "France": "フランス", "Germany": "ドイツ",
    "Greece": "ギリシャ", "Hungary": "ハンガリー",
    "Iceland": "アイスランド", "Ireland": "アイルランド",
    "Italy": "イタリア", "Kosovo": "コソボ", "Latvia": "ラトビア",
    "Lithuania": "リトアニア", "Luxembourg": "ルクセンブルク",
    "Macedonia": "北マケドニア", "Malta": "マルタ",
    "Montenegro": "モンテネグロ",
    "Netherlands": "オランダ", "Norway": "ノルウェー",
    "Poland": "ポーランド", "Portugal": "ポルトガル",
    "Romania": "ルーマニア", "Russia": "ロシア", "Serbia": "セルビア",
    "Slovakia": "スロバキア", "Slovenia": "スロベニア",
    "Spain": "スペイン", "Sweden": "スウェーデン",
    "Switzerland": "スイス", "Turkey": "トルコ",
    "Ukraine": "ウクライナ", "United Kingdom": "イギリス",
    # --- アジア ---
    "Bangladesh": "バングラデシュ", "Bhutan": "ブータン",
    "Cambodia": "カンボジア", "India": "インド",
    "Indonesia": "インドネシア", "Israel": "イスラエル",
    "Japan": "日本", "Jordan": "ヨルダン",
    "Kyrgyzstan": "キルギス",
    "Laos": "ラオス", "Lebanon": "レバノン",
    "Malaysia": "マレーシア", "Mongolia": "モンゴル",
    "Nepal": "ネパール",
    "Palestine": "パレスチナ", "Philippines": "フィリピン",
    "Qatar": "カタール", "South Korea": "韓国",
    "Singapore": "シンガポール",
    "Sri Lanka": "スリランカ", "Taiwan": "台湾",
    "Thailand": "タイ", "United Arab Emirates": "アラブ首長国連邦",
    "Vietnam": "ベトナム",
    # --- アフリカ ---
    "Botswana": "ボツワナ", "Egypt": "エジプト",
    "eSwatini": "エスワティニ", "Ghana": "ガーナ", "Kenya": "ケニア",
    "Lesotho": "レソト", "Madagascar": "マダガスカル",
    "Namibia": "ナミビア", "Nigeria": "ナイジェリア",
    "Rwanda": "ルワンダ", "Senegal": "セネガル",
    "South Africa": "南アフリカ",
    "Tunisia": "チュニジア", "Uganda": "ウガンダ",
    # --- 北米・中米 ---
    "Canada": "カナダ", "United States of America": "アメリカ",
    "Mexico": "メキシコ", "Guatemala": "グアテマラ",
    "Dominican Rep.": "ドミニカ共和国", "Greenland": "グリーンランド",
    "Costa Rica": "コスタリカ", "Panama": "パナマ",
    "Puerto Rico": "プエルトリコ",
    # --- 南米 ---
    "Argentina": "アルゼンチン", "Bolivia": "ボリビア",
    "Brazil": "ブラジル", "Chile": "チリ", "Colombia": "コロンビア",
    "Ecuador": "エクアドル", "Paraguay": "パラグアイ",
    "Peru": "ペルー", "Uruguay": "ウルグアイ",
    # --- オセアニア ---
    "Australia": "オーストラリア", "New Zealand": "ニュージーランド",
    "Vanuatu": "バヌアツ",
}


def is_covered(ne_name):
    return ne_name in COVERED


def ja(ne_name):
    return COVERED.get(ne_name, ne_name)
