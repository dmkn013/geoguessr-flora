# -*- coding: utf-8 -*-
"""種ごとに「どのWikipedia記事の代表画像を取るか」を明示する。

学名をそのまま引くと外れる。前回コルクガシで
「記事の代表画像に肝心の剥皮された赤い幹が写っていない」という失敗をした。
記事の代表画像は"その記事の顔"であって"見分け方の写真"ではない。

そこで種ごとに、GeoGuessrで実際に手がかりになる特徴が
写っている見込みの高い記事を選ぶ。titles は英語版の記事名。
複数書いた場合は上から順に試し、取れたものを使う。
"""

# id -> 英語版Wikipediaの記事名（優先順）
QUERIES = {
    "eucalyptus":    ["Eucalyptus", "Eucalyptus regnans"],
    "grasstree":     ["Xanthorrhoea", "Xanthorrhoea preissii"],
    "treefern":      ["Dicksonia antarctica", "Cyathea"],
    "cordyline":     ["Cordyline australis"],
    "baobab":        ["Adansonia grandidieri", "Adansonia digitata"],
    "acacia":        ["Vachellia tortilis"],
    "oilpalm":       ["Elaeis guineensis"],
    "doum":          ["Hyphaene thebaica"],
    "cecropia":      ["Cecropia"],
    "araucaria_ang": ["Araucaria angustifolia"],
    "araucaria_arau":["Araucaria araucana"],
    "nothofagus":    ["Nothofagus", "Nothofagus pumilio"],
    "caatinga":      ["Caatinga"],
    "saguaro":       ["Saguaro"],
    "joshua":        ["Yucca brevifolia"],
    "spanishmoss":   ["Spanish moss"],
    "ponderosa":     ["Pinus ponderosa"],
    "sugarmaple":    ["Acer saccharum"],
    "olive":         ["Olive"],
    # 剥皮された幹が主題の記事を先に引く（樹木そのものの記事だと幹が写らない）
    "corkoak":       ["Cork (material)", "Quercus suber"],
    "stonepine":     ["Pinus pinea"],
    "cypress":       ["Cupressus sempervirens"],
    "maritimepine":  ["Pinus pinaster"],
    "birch":         ["Betula", "Betula pendula"],
    "spruce":        ["Picea abies"],
    "larch":         ["Larix", "Larix decidua"],
    "scotspine":     ["Pinus sylvestris"],
    "rubber":        ["Hevea brasiliensis"],
    "coconut":       ["Cocos nucifera"],
    "betel":         ["Areca catechu"],
    "teak":          ["Tectona grandis"],
    "banana":        ["Banana", "Musa (genus)"],
    "sugi":          ["Cryptomeria"],
    "bamboo":        ["Bamboo"],
    "ginkgo":        ["Ginkgo biloba"],
    "datepalm":      ["Phoenix dactylifera"],
    "washingtonia":  ["Washingtonia robusta"],
    "vineyard":      ["Vineyard"],
    "poplar":        ["Populus nigra", "Populus"],
    "spinifex":      ["Triodia (plant)"],
    "aspen":         ["Populus tremuloides"],
    "blackspruce":   ["Picea mariana"],
    "douglasfir":    ["Pseudotsuga menziesii"],
    "saxaul":        ["Haloxylon ammodendron", "Haloxylon"],
    "sal":           ["Shorea robusta"],
    "mangrove":      ["Mangrove", "Rhizophora mangle"],
    "agave":         ["Agave americana", "Agave"],
    "paulownia":     ["Paulownia tomentosa"],
}


# ---------------------------------------------------------------------------
# 目視1巡目で落ちたもの。
#
# 落ちた原因はほぼ1つ: `prop=pageimages` は記事の**先頭画像**を返すが、
# 植物記事の先頭画像は「19世紀の植物図版」か「果実のクローズアップ」であることが多い。
# 図鑑としては正しくても、GeoGuessrで見るのは**道端から見た木の形と樹皮**なので使えない。
#
# 対策として、種そのものの記事ではなく
#   - 栽培・林業・景観の記事（プランテーション、並木、林）
#   - その特徴が主題の記事
# を引く。それでも駄目なら Commons のカテゴリ検索に切り替える（fetch側で対応）。
RETRY = {
    # 図版が返ってきた組
    "oilpalm":  ["Oil palm plantation", "Elaeis"],
    "rubber":   ["Rubber tree plantation", "Natural rubber", "Hevea"],
    "coconut":  ["Coconut palm", "Cocos"],
    "sugi":     ["Sugi", "Cryptomeria japonica"],
    "sal":      ["Sal forest", "Shorea"],
    # 果実・葉のクローズアップが返ってきた組
    "eucalyptus": ["Eucalypt", "Eucalyptus forest"],
    "banana":     ["Banana plantation", "Musa acuminata"],
    "teak":       ["Teak plantation", "Tectona"],
    "datepalm":   ["Date palm grove", "Phoenix (plant)"],
    "olive":      ["Olive grove", "Olea"],
    "sugarmaple": ["Maple", "Acer saccharum subsp. nigrum"],
    # 樹木ではなく製品が返ってきた
    "corkoak":    ["Quercus suber", "Cork oak forest", "Montado"],
}

