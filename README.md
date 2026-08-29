# geoguessr-flora

GeoGuessr の植生メタを学ぶための世界地図。**48種 / 2,785点**を色分けしてプロットし、
点にカーソルを合わせると種名・示す地域・座標が、クリックすると見分け方と
「誤爆しやすい罠」が出る。成果物は自己完結した1枚の HTML。

公開先: https://claude.ai/code/artifact/6075d72d-176c-4719-ba97-5f40199e7361

## 構成

```
src/    生成スクリプト
data/   入力と中間データ（world110m.json は world-atlas から取得済み）
dist/   成果物（flora_atlas.html）と確認用プレビュー画像
```

| ファイル | 役割 |
|---|---|
| `src/species.py` | 48種の定義（名前・示す地域・見分け方・罠）。**内容の主体はここ** |
| `src/ranges.py` | 種ごとの分布域（緯度経度の矩形＋重み） |
| `src/palette.py` | tab10 の10色を「近い種が同色にならないように」割り当てる |
| `src/sample_points.py` | 分布域から点をサンプリングし、陸地判定で海の点を弾く |
| `src/topo_to_svg.py` | TopoJSON → SVG パス（正距円筒投影） |
| `src/build_atlas.py` | HTML を組み立てる |
| `src/preview_map.py` / `preview_dots.py` | 地図と点の見え方を PNG で目視確認する検算用 |

## 作り直す

```bash
python src/topo_to_svg.py      # data/land_path.txt
python src/sample_points.py    # data/points.json（乱数シード固定・再現する）
python src/build_atlas.py      # dist/flora_atlas.html
python src/preview_dots.py     # dist/dots_preview.png（明暗テーマで点が沈まないか確認）
```

依存は `Pillow` のみ（プレビュー用）。本体の生成は標準ライブラリだけで動く。

## 設計上の判断

- **色は種の識別ではなく「隣り合う種の区別」**。48色に分けても人間は見分けられないので、
  地図の四色定理と同じ考え方で10色を割り当てている。種の識別はホバーのラベルが担う。
  48種で同色ペアの最小距離は 19.3度を確保（`palette.py` が検算を出す）。
- **点は分布域からのサンプリング**。手打ちのアンカーではカバー率が上がらなかった。
  海に落ちた点は、地図に使っているのと同じ陸地ポリゴンで弾く
  （別ソースを使うと「地図では海なのに点がある」というズレが出る）。
- **投影は正距円筒**。緯度経度からピクセルへの変換が1行で済み、点の配置と
  ホバー判定が単純になる。教材としては面積の正確さより緯度感覚が重要。
- **日付変更線をまたぐリングはパスを切る**。切らないと地図を横断する帯が出る
  （フィジー約17°S・チュクチ半島約70°N で実際に発生した）。
- **空白は埋めない**。サハラ内陸・北極圏・北米大平原に点が無いのは意図的で、
  手がかりになる植生が無い場所を埋めると教材として嘘になる。

## 未了

- **実写画像が入っていない**。詳細パネルに「Mapillary の取得待ち」と出る。
  - Wikipedia の代表画像（`prop=pageimages`）は**認証不要で取得できることを確認済み**。
    4種で実際に画像を見て、種と特徴が写っていることまで検証した。
    ただし Wikimedia はレート制限が厳しいので **1.5秒間隔＋連絡先入り User-Agent** が要る
    （連続で叩くと `Too many requests` が HTML で返り、壊れた JPEG として保存される）。
  - Mapillary（CC-BY-SA・要トークン）は車載目線なので本番の見え方に近い。
    トークンは https://www.mapillary.com/dashboard/developers で Register Application。
  - 図鑑寄りの Wikipedia と車載目線の Mapillary は役割が違うので、両方入れる方針。
- 画像は Artifact の 16MB 制限に収める必要があるため、点ごとではなく**種ごとに2〜3枚**。
