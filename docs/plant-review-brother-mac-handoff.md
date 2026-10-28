# 弟のMacで継続して植物画像を確認する

## 担当と上限

- GitHub: dmkn013/geoguessr-flora。弟: tetsujg79-hub / TTsu。招待を承諾し、自分の別契約Codexを使う。
- 固定割当: `data/plant_review_assignments/brother-mac-20261028.json` の **8,985枚**。川崎は残り8,888枚。旧100枚割当はsuperseded。
- 100枚は上限ではない。最初の10枚は速度と消費の校正として記録するが、検証に問題がなければ承認待ちで止まらず次へ進む。最終的に担当全件を処理する。
- 分担を変更するのは中央のみ。全体完了数は中央取込済みのユニーク画像IDで数える。

## Macの初回セットアップ

Python 3、Git、GitHub CLI、Codexを使用。GitHub CLIがなければ本人の通常の方法で導入する。管理者設定や別ユーザーのセッションを変更しない。

```bash
gh auth login
git clone --single-branch --branch main https://github.com/dmkn013/geoguessr-flora.git
cd geoguessr-flora
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-review.txt
git switch -c review/brother-mac-20261028
python src/review_worker.py next --download --limit 4
```

新しいターミナルでは `source .venv/bin/activate`。中央PCの絶対パスやFLORA_CANDIDATES設定は不要。`review_worker.py`がローカルの`.review-cache/random/`を使う。画像はdraft release `plant-review-images-20261028`から500枚単位で必要分だけ取得し、割当ファイルのSHA256と全画像を照合する。招待承諾済みのwrite権限アカウントで認証すること。画像はGitへ追加しない。

Macの実機動作は未確認。Windows上で同じPython経路と配布画像の取得・ハッシュ検査を検証する。初回にMacで環境不備があればエラーを記録し、未確認画像の結果を作らない。

## Codexへの作業指示

この文書と `docs/plant-review-runbook.md` の画像判定基準を守り、自分の割当8,985枚を小バッチで継続してください。全景・左右端・前景・背景を実視認し、植物ごとに矩形[x,y,width,height]、最も詳しい確実な分類、根拠、候補、不足形質を記録します。個体分離不能な群落はgroup。種以下も診断形質があれば検討しますが、形質を推測で補完しません。切出しは元画素の縦横比を維持。国・座標・分布・文字・道路・旧タグを同定根拠にしません。

画像を実表示する前に記録しない。全景の一次確認はscreened。必要拡大・全対象の記録後、矩形を元画像へ重ねた画像を実際に見てから全objectsのqa_checked=trueとcompleteにします。completeは種判明数ではありません。種以下confirmedには学名、類似候補との診断比較、一次資料HTTPS URLとsupportsを必須とします。

```bash
python src/plant_review.py example
python src/review_worker.py save .review-cache/input.json
python src/review_worker.py validate
python src/review_worker.py stats
python src/review_worker.py next --download --limit 4
```

入力JSONのexpected_revisionはnextの値を使う。結果は自分専用の `worker_results/brother-mac/brother-mac-20261028/` へ保存され、中央のdata/plant_reviewsへは直接書きません。historyも保持。割当外の保存は拒否されます。

辞書にない分類は `worker_results/brother-mac/proposed_taxa.json` に正式名・学名・rank・親・一次資料URLを提案し、その対象は既存の確実な上位分類と候補で記録する。中央辞書は直接変更しない。表示・解析・生成HTMLは川崎が担当する。

## 使用枠から毎回の枚数を決める

弟自身のアカウント使用率を開始・終了と最大4枚ごとに取得する。川崎の使用率とは独立。厳密なトークン数は分からないのでアカウント使用率の観測値を使用し、他用途の消費も含むことを明記する。

`src/review_budget.py`のplanは、通常5時間70%・週間80%を予算上限にして残り毎時枠へ配分する。直近20回の1枚当たり使用率・時間の90パーセンタイルへ25%上乗せ。1回20分相当まで＋保存検証5分、最大12枚、4枚ごと再確認。初回は4枚以下で計測。5時間70%到達は通常作業を保留し30%を残す。85%は緊急停止基準で15%の残枠を確保。週間80%以上は新規大量判定保留。5時間枠と週間枠はそれぞれの実測差分で独立に計算する。週間差分0も無消費とはみなさず、整数丸めの余裕を取る。リセットを跨いだ差分は学習に使わない。

```bash
# 数値は例。実際の使用率とリセットまでの残時間に置き換える
python src/review_budget.py --log worker_usage/brother-mac.jsonl plan --used5 10 --weekly 20 --hours5 4 --hours-week 100
python src/review_budget.py --log worker_usage/brother-mac.jsonl report --start5 10 --end5 12 --start-weekly 20 --end-weekly 20 --complete 4 --minutes 8
```

planが0枚なら、その回は保存・使用率記録だけ。使用率を取得できなければ大量処理せず不明と記録。追加課金やAPI契約はしない。初回計測が済んだら、弟本人のMac利用の了承範囲でCodexへ毎時・25分以内の継続予約を設定してよい。通常の小進捗や変化のない保留は通知せず、大きな進展・失敗・判断が必要な時のみ通知する。

## 結果をPRで継続返却する

10〜30枚程度の小さい区切りで保存・validate後にcommit/pushし、作業用PRを作る。PR提出は作業停止条件ではない。続ける場合は同じ未merge PRを更新する。merge後は最新mainを取り込んで次のブランチへ進み、同じ画像をやり直さない。

```bash
python src/review_worker.py validate
git add worker_results/brother-mac worker_usage/brother-mac.jsonl
git commit -m "植物画像の分担確認結果を追加"
git push -u origin HEAD
gh pr create --base main --title "植物画像の分担確認結果" --body-file .review-cache/pr-body.md
```

PR本文に割当ID・実確認数・complete数・screened数・矩形数・種以下確定数・実作業時間・使用モデル・使用率前後・主な保留理由を記載する。個人ログや認証情報は含めない。自分の結果と使用率ログ以外をcommitしない。`.review-cache/`・画像・venvはGit無視。

## 川崎側の取り込み

PRの画像ID・割当・原画像SHA256・schema・辞書・QAを検査し、最初の10枚は全件、以後は種以下確定・新分類・不確実な対象を重点的に目視照合する。PRの結果は提案であり、そのまま確定集計に入らない。対象フォルダをローカルへ取得して検査だけを先に実行する。

```powershell
python src/import_plant_worker.py worker_results/brother-mac/brother-mac-20261028 --assignment data/plant_review_assignments/brother-mac-20261028.json
# 中央の目視照合と辞書承認後のみ。既に取り込んだIDは除いたフォルダを渡す
python src/import_plant_worker.py 未取込分フォルダ --assignment data/plant_review_assignments/brother-mac-20261028.json --apply
python src/plant_review.py validate
python src/plant_review.py build
python src/build_index.py
```

取り込みは既存記録があれば拒否し上書きしない。PRをmergeしてもworker_resultsに入るだけで中央集計は変わらず、中央がapply後の記録と生成物を別commitで反映する。worker側の履歴と元reviewed_at・レコードハッシュを保持。全8,985枚の取り込み後のみ割当完了とする。
