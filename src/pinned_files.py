# -*- coding: utf-8 -*-
"""検索でどうしても実写が取れなかった種の、Commons ファイル名の直指定。

検索語をいくら工夫しても
「油ヤシ→衛星画像」「ナツメヤシ→岩山」「オリーブ→庭の小道」のように
無関係な画像が上位に来た。関連度の当てずっぽうを続けるより、
**ファイルを名指しして目視で確かめる**ほうが確実で早い。

候補は複数書く。1枚目が取れなければ次を試す。
"""

# 2巡目: カテゴリを実際に列挙して、存在するファイル名から選んだもの。
# 1巡目は**ファイル名を推測で書いて全滅した**（存在しない名前ばかりだった）。
# 名前を作るのではなく、あるものから選ぶこと。
PINNED = {
    # 1巡目の画像は崖に生える広がった樹形の野生種で、
    # tells の「細く直立した濃緑の円柱」が写っていなかった。
    # GeoGuessr で手がかりになるのは栽培された円柱形なのでそちらに差し替える。
    # 剥皮された赤褐色の幹が明確に写っている数少ない1枚。
    # montado の景観写真では tells の「幹の下半分だけ樹皮が剥がされて赤茶色」
    # が見えず、3回の引き継ぎで持ち越していた。
    "corkoak": [
        "A Cork Tree - Apr 2011.jpg",
        "2026-03-07 Cork oak in A dos Negros.jpg",
    ],
    "cypress": [
        "Cipressi con edicola San Damiano.jpg",
        "Caravaggio, viale del cimitero.jpg",
        "Cimitero monumentale e cipressi a Salò.jpg",
    ],
    "oilpalm": [
        "Oil palm plantation in Cigudeg-03.jpg",
        "Palm oil plantation in Indonesia.jpg",
    ],
    "rubber": [
        "Large rubber plantation in Vietnam.jpg",
        "A Hevea brasiliensis farm in Dong Nam Bo, Vietnam.jpg",
        "Plantation dhévéas (Cu Chi) (6819418639).jpg",
    ],
    "teak": [
        "Forest plantation of Tectona grandis in Costa Rica (2017).jpg",
        "Bénin-Tectona grandis (1).jpg",
    ],
    "datepalm": [
        "Chinguetti oasis.jpg",
        "4 date palms 1.jpg",
    ],
    "olive": [
        "Birgi 15 05 1990 alte Ölbaumkultur.jpg",
        "Aphrodite Nature Trail, Cyprus, view to bay across olive garden.jpg",
    ],
    "sugarmaple": [
        "A strikingly Yellow Sugar Maple tree in Guelph, Ontario.jpg",
    ],
    "banana": [
        "Banana plantation near Vang Vieng.jpg",
        "Banana plantation, Ecuador.jpg",
        "Banana farm.jpg",
    ],
    "sal": [
        "Sal forests in Purulia, West Bengal, India.jpg",
        "Sal (Shorea robusta) forests as avenue.jpg",
    ],
}
