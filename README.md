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
| `src/wiki_queries.py` | 種ごとに「どの記事の画像を取るか」（学名そのままだと外れる） |
| `src/fetch_wikipedia.py` | Wikipedia から実写を取得（1.5秒間隔・UA必須） |
| `src/refetch_wikipedia.py` / `pinned_files.py` / `refetch_pinned.py` | 目視で落ちた種を取り直す |
| `src/list_commons.py` | Commons のカテゴリを列挙して差し替え候補を選ぶ |
| `src/review_photos.py` | 48種のコンタクトシートを作り、**1枚ずつ目視する** |
| `src/embed_photos.py` | 採用画像を縮小し data URI にして `data/photos.json` へ |

## 作り直す

```bash
python src/topo_to_svg.py      # data/land_path.txt
python src/sample_points.py    # data/points.json（乱数シード固定・再現する）
python src/embed_photos.py     # data/photos.json（data/photos_raw/ から）
python src/build_atlas.py      # dist/flora_atlas.html
python src/preview_dots.py     # dist/dots_preview.png（明暗テーマで点が沈まないか確認）
```

画像を取り直す場合（`data/photos_raw/` が空のとき）:

```bash
python src/fetch_wikipedia.py  # 48種ぶん取得。1.5秒間隔なので約5分かかる
python src/review_photos.py    # dist/photo_review.png を目視する
```

`data/photos_raw/` の画像はリポジトリに入れていない（20MB あるため）。
`_meta.json` に「どの記事のどのファイルを使ったか」が残るので、取得は再現できる。

依存は `Pillow` のみ。地図とHTMLの生成は標準ライブラリだけで動く。

## 見る

`dist/flora_atlas.html` を**ブラウザで直接開くだけ**（サーバ不要）。
画像も地図も埋め込み済みで、外部通信は Google Fonts だけ。
オフラインでもフォントが代替に落ちるだけで中身は完全に動く。

## 点の作り方（2系統ある）

### 確認済みの点（本来の設計・実装済み／トークン待ち）

    ランダムに地点を引く → その地点の Mapillary 車載写真を取る
      → その植物が画面に写っているか目視 → 写っていれば残す / 写っていなければ捨てて次へ

**1点1点が実際の写真で裏付けられた点**になる。
Mapillary を使うのは CC-BY-SA で保存・再配布できるため
（Street View は規約上、取得画像を保存・再配布できない）。

| スクリプト | 役割 |
|---|---|
| `src/mapillary.py` | API ラッパ。トークンは `data/.mapillary_token` か環境変数 |
| `src/verify_points.py` | 候補をランダムに引き、その地点の写真を集める |
| `src/review_candidates.py` | 候補写真を並べて**目視で採否**を決める |
| `src/build_verified.py` | 採用された点を `data/verified_points.json` に集約 |

```bash
python src/verify_points.py eucalyptus        # 候補の写真を集める
python src/review_candidates.py sheet eucalyptus       # 並べて見る
python src/review_candidates.py accept eucalyptus 0 3 5   # 写っていたものを採用
python src/build_verified.py
```

**判定を自動化していないのは意図的**。種の同定を画像認識に任せると
誤判定した点が「確認済み」として混ざり、この方式の意味が無くなる。

### 表示用の点（現行の2,785点）

`ranges.py` の分布域から `sample_points.py` が乱数で散らし、陸地判定を通したもの。
**個々の点にその植物がある確認は無い**。分布の濃さを見るための表示。
確認済みの点が貯まるまでの繋ぎで、混同しないよう画面にも明記してある。

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

## 実写のどこを見るか（注釈）

詳細パネルの写真には**「どこを見るか」の枠**が重ねてある（48種・93枠）。
座標は `annotations.py` に 0〜1 の相対値で持っているので、画像を縮小しても崩れない。
「枠」ボタンで表示を切り替えられる。

**自動検出は使っていない。** 誤検出した枠は「ここを見ろ」と自信ありげに
間違った場所を指すことになり、枠が無いより悪い。
`check_annotations.py` で1枚ずつ描画して目視で確かめたものだけを入れている。
写真にその特徴が写っていない場合は、無い特徴を指す枠を作らず、
**写っているものだけに枠を付ける**（ポプラ並木がその例）。

## 実写画像

**48種すべてに Wikipedia / Wikimedia Commons の実写が入っている**（各1枚・計3.8MB）。
判定は「その種の `tells[0]`＝最初に見る特徴が写っているか」で、48種すべて目視した。

`prop=pageimages` が返すのは記事の**先頭画像**で、植物記事では
植物図版・果実のクローズアップ・製品写真になりがちだった（48種中12種がこれで落ちた）。
差し替えの経緯と教訓は `docs/photo-review.md` にある。

## 未了

- **コルクガシの画像が特徴と一致していない**。現在は montado の景観で、
  最大の手がかりである**剥皮された赤褐色の幹が写っていない**。
  `tells[0]` と画像がずれている唯一の種なので、直すならここから。
- **Mapillary（車載目線）は未着手**。要トークンで、
  https://www.mapillary.com/dashboard/developers の Register Application で発行する。
  図鑑寄りの Wikipedia と役割が違うので両方入れる方針は変えていない。
  Artifact の 16MB 制限に対して現在 4.2MB なので、種ごとにもう1〜2枚足す余地はある。

## 引き継ぎ

作業の経緯・詰まった点・次にやることは `docs/` の日付順ハンドオフにある
（最新: `docs/2026-08-30-handoff.md`）。
ダイアリー（OneDrive）と同じ内容だが、**PC間でOneDriveが同期していない事故があった**ため
リポジトリ内にも置いてある。こちらを正とする。
