#!/usr/bin/env bash
# dist/ を gh-pages ブランチへ直接配信する。
#
# なぜ Actions を使わないか:
#   写真が 892MB ある。main に入れると git 履歴に永久に残り、
#   リポジトリが 2GB 近くなる（GitHub の推奨は 1GB）。
#   gh-pages を毎回作り直して force push すれば、履歴は常に1世代分
#   しか持たない。main はコードだけで軽いままにできる。
#
# 使い方:
#   bash deploy_pages.sh
#
# 事前に生成しておくもの:
#   python src/build_photos.py    # dist/photos/  (892MB)
#   python src/build_index.py     # dist/index.html
set -euo pipefail

cd "$(dirname "$0")"
REPO=$(git config --get remote.origin.url)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

if [ ! -d dist/photos ] || [ -z "$(ls -A dist/photos 2>/dev/null)" ]; then
  echo "dist/photos が空です。先に python src/build_photos.py を実行してください。" >&2
  exit 1
fi

echo "dist/ をコピー中..."
cp -r dist/. "$TMP/"
# Jekyll に処理させない（_ 始まりのファイルが無視されるのを防ぐ）
touch "$TMP/.nojekyll"

cd "$TMP"
git init -q
git checkout -qb gh-pages
git add -A
git -c user.name="deploy" -c user.email="deploy@local" \
    commit -qm "Deploy $(date '+%Y-%m-%d %H:%M')"

echo "push 中（初回は892MBあるので数分かかります）..."
git push -qf "$REPO" gh-pages

echo "完了: https://dmkn013.github.io/geoguessr-flora/"
echo "  Pages の設定を「gh-pages ブランチ / (root)」にしてください（初回のみ）"
