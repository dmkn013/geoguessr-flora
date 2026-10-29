"""位置情報を伏せた植物単位の再判定。既存タグと元画像は変更しない。"""
import argparse
import hashlib
import html
import json
import math
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from paths import CANDIDATES, DATA, DIST
from taxon_hierarchy import parent_names, summarize_tags

RECORDS = DATA / 'plant_reviews'
RAW = CANDIDATES.parent / 'random'
DEADLINE = datetime.fromisoformat('2026-11-12T10:10:00+09:00')
RANKS = {'unknown', 'family', 'subfamily', 'genus', 'section', 'species_group',
         'species', 'subspecies', 'variety', 'form', 'cultivar', 'hybrid'}
FINE = {'species', 'subspecies', 'variety', 'form', 'cultivar', 'hybrid'}


def load(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def index():
    return {i['img_id']: i for i in load(DATA / 'random_index.json')}


def records():
    return {p.stem: load(p) for p in RECORDS.glob('*.json')}


def image_path(img_id, idx):
    path = (RAW / idx[img_id]['file']).resolve()
    if not path.is_relative_to(RAW.resolve()):
        raise ValueError('元画像のパスが画像フォルダ外です')
    return path


def validate(record, idx, verify_image=False):
    """矩形と判断の根拠を検証。分類名の正しさは別途目視QAする。"""
    img_id = record.get('image_id')
    if img_id not in idx:
        raise ValueError(f'インデックスにない画像: {img_id}')
    if record.get('schema_version') != 1:
        raise ValueError('schema_version は1です')
    if record.get('status') not in {'screened', 'complete'}:
        raise ValueError('status は screened または complete')
    if record.get('viewed_full_image') is not True:
        raise ValueError('元画像全景の確認が必要です')
    if not isinstance(record.get('reviewer'), str) or not record['reviewer'].strip():
        raise ValueError('reviewerが必要です')
    if not isinstance(record.get('image_notes'), str) or not record['image_notes'].strip():
        raise ValueError('全景の確認内容と見落とし/分類限界をimage_notesに記録してください')
    objects = record.get('objects')
    if not isinstance(objects, list):
        raise ValueError('objectsはリストです')
    if not objects and record.get('empty_reason') not in {'no_visible_plants', 'not_identifiable', 'unusable_image'}:
        raise ValueError('対象なしの場合はempty_reasonを指定してください')
    seen = set()
    for obj in objects:
        oid = obj.get('object_id')
        if not isinstance(oid, str) or not oid or oid in seen:
            raise ValueError('object_idは画像内で一意の文字列にしてください')
        seen.add(oid)
        box = obj.get('bbox')
        if not isinstance(box, list) or len(box) != 4 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in box):
            raise ValueError('bboxは有限値の[x,y,width,height]です')
        x, y, w, h = box
        if not (0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x+w <= 1.000001 and y+h <= 1.000001):
            raise ValueError('bboxが画像の範囲外または面積0です')
        if obj.get('scope') not in {'individual', 'group'}:
            raise ValueError('scopeはindividualまたはgroup')
        taxon = obj.get('taxon', {})
        if taxon.get('rank') not in RANKS or not taxon.get('name'):
            raise ValueError('taxonのnameとrankが必要です')
        if obj.get('certainty') not in {'confirmed', 'provisional', 'unidentified'}:
            raise ValueError('certaintyが不正です')
        if not isinstance(obj.get('evidence'), list) or not obj['evidence'] or any(not isinstance(s, str) or not s.strip() for s in obj['evidence']):
            raise ValueError('見えた形質をevidenceに列挙してください')
        if not isinstance(obj.get('limitations'), str) or not obj['limitations'].strip():
            raise ValueError('より下位に同定できない理由が必要です')
        for key in ('candidates', 'morphology', 'sources'):
            if not isinstance(obj.get(key), list):
                raise ValueError(f'{key}はリストです')
        if obj['certainty'] == 'confirmed' and taxon['rank'] in FINE:
            if not taxon.get('scientific_name') or not obj.get('diagnostic_comparison'):
                raise ValueError('種以下の確定には学名と類似候補との識別点が必要です')
            if not obj['sources'] or any(not isinstance(s, dict) or not str(s.get('url', '')).startswith('https://') or not s.get('supports') for s in obj['sources']):
                raise ValueError('種以下の確定には識別根拠の資料URLとsupportsが必要です')
    if verify_image:
        path = image_path(img_id, idx)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if record.get('source_sha256') != actual:
            raise ValueError(f'元画像のハッシュ不一致: {img_id}')
        with Image.open(path) as im:
            if record.get('source_size') != list(im.size):
                raise ValueError('元画像寸法が不一致です')


def save(path):
    r = load(Path(path))
    # 位置や候補という表示説明を正式な分類タグと混同しない。
    catalog = load(DATA / 'taxon_catalog.json', {})
    for obj in r.get('objects', []):
        taxon = obj.get('taxon', {})
        entry = catalog.get(taxon.get('scientific_name'))
        if entry:
            if taxon.get('rank') != entry['rank']:
                raise ValueError('学名と分類階級が辞書に一致しません')
            if taxon.get('name') != entry['name']:
                obj.setdefault('label', taxon.get('name', ''))
                taxon['name'] = entry['name']
    idx = index()
    validate(r, idx)
    dest = RECORDS / f"{r['image_id']}.json"
    RECORDS.mkdir(parents=True, exist_ok=True)
    lock = RECORDS / f"{r['image_id']}.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        old = load(dest)
        expected = r.pop('expected_revision', 0)
        if expected != (old['revision'] if old else 0):
            raise ValueError('revision不一致。既存結果を読んでから修正してください')
        src = image_path(r['image_id'], idx)
        r['source_sha256'] = hashlib.sha256(src.read_bytes()).hexdigest()
        with Image.open(src) as im:
            r['source_size'] = list(im.size)
        r['revision'] = expected + 1
        r['reviewed_at'] = datetime.now(timezone.utc).isoformat()
        validate(r, idx, verify_image=True)
        if old:
            atomic(RECORDS / 'history' / f"{r['image_id']}-{old['revision']}.json", old)
        atomic(dest, r)
        print(f"保存: {r['image_id']} / {r['status']} / {len(r['objects'])}対象 / revision {r['revision']}")
    finally:
        os.close(fd)
        lock.unlink()


def next_images(limit, include_screened=True):
    idx, done = index(), records()
    tags = load(DATA / 'tags.json', {})
    reserved = set()
    for manifest in (DATA / 'plant_review_assignments').glob('*.json'):
        assignment = load(manifest)
        if assignment.get('state') == 'reserved':
            reserved.update(assignment['image_ids'])
    ids = [i for i in idx if i not in reserved and
           (i not in done or (include_screened and done[i]['status'] == 'screened'))]
    # 座標・旧ラベルは出さない。順序も地理と無関係なハッシュにする。
    ids.sort(key=lambda i: (not bool(tags.get(i)), hashlib.sha256(i.encode()).hexdigest()))
    for i in ids[:limit]:
        path = image_path(i, idx)
        with Image.open(path) as im:
            size = list(im.size)
        print(json.dumps({'image_id': i, 'path': str(path), 'size': size,
                          'expected_revision': done.get(i, {}).get('revision', 0)}, ensure_ascii=False))


def stats():
    idx, rows = index(), records()
    stages = Counter(r['status'] for i, r in rows.items() if i in idx)
    complete = stages['complete']
    objects = [o for i, r in rows.items() if i in idx for o in r['objects']]
    fine = [o for o in objects if o['certainty'] == 'confirmed' and o['taxon']['rank'] in FINE]
    qa_pending = sum(not o.get('qa_checked', False) for o in fine)
    hours = max(0, (DEADLINE - datetime.now(timezone.utc)).total_seconds()/3600)
    result = {'total': len(idx), 'complete': complete, 'screened_only': stages['screened'],
              'unseen': len(idx)-len(idx.keys() & rows.keys()), 'objects': len(objects),
              'confirmed_species_or_below': len(fine), 'fine_qa_pending': qa_pending,
              'box_qa_pending': sum(not o.get('qa_checked', False) for o in objects),
              'remaining': len(idx)-complete, 'deadline_jst': DEADLINE.isoformat(),
              'hours_left': round(hours, 1),
              'required_complete_per_hour': math.ceil((len(idx)-complete)/hours) if hours else None}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build():
    idx, rows = index(), records()
    out = DIST / 'plant_reviews'
    photos = DIST / 'review_photos'
    out.mkdir(parents=True, exist_ok=True)
    photos.mkdir(parents=True, exist_ok=True)
    public = {}
    for i, r in rows.items():
        validate(r, idx, verify_image=True)
        atomic(out / f'{i}.json', r)
        dst = photos / f'{i}.jpg'
        src = image_path(i, idx)
        if not dst.exists() or hashlib.sha256(dst.read_bytes()).hexdigest() != r['source_sha256']:
            shutil.copyfile(src, dst)
        public[i] = r
    # ローカルビューは元画像の全景。地図用に切り出された写真と混同しない。
    cards = []
    for i, r in sorted(public.items()):
        cards.append(f'<article><h2>{html.escape(i)}</h2><p>{html.escape(r["image_notes"])}</p>'
                     f'<div class="shotbox" data-image-id="{i}"><div class="plant-stage"><img src="review_photos/{i}.jpg" alt="元画像の全景"></div></div></article>')
    page = '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>植物ごとの同定レビュー</title><link rel="stylesheet" href="plant_boxes.css">
<style>body{font-family:system-ui;background:#f5f4ef;color:#182d26;margin:24px auto;max-width:1150px;padding:0 16px}article{background:white;padding:20px;margin:24px 0;border-radius:12px}h2{font-size:16px}.shotbox{overflow:hidden}.plant-stage img{width:100%;display:block}</style>
<h1>植物ごとの同定レビュー</h1><p>番号の枠と植物名が対応します。項目を選ぶと対象部分を拡大できます。候補は確定した分類と区別して表示します。</p>
''' + ''.join(cards) + '<script src="plant_boxes.js"></script><script>document.querySelectorAll("[data-image-id]").forEach(b=>PlantBoxes.attach(b,b.querySelector(".plant-stage"),b.dataset.imageId));</script></html>'
    (DIST / 'plant_review.html').write_text(page, encoding='utf-8')
    # 学名確定かつQA済みの結果だけを集約。旧tags.jsonの破壊的更新はしない。
    effective = {}
    for i, r in rows.items():
        if r['status'] != 'complete' or any(o['certainty'] == 'confirmed' and o['taxon']['rank'] in FINE and not o.get('qa_checked', False) for o in r['objects']):
            continue
        effective[i] = list(dict.fromkeys(o['taxon']['name'] for o in r['objects']
                            if o['certainty'] == 'confirmed' and
                            (o['taxon']['rank'] not in FINE or o.get('qa_checked', False))))
    parents = parent_names(load(DATA / 'taxon_catalog.json', {}))
    summary = summarize_tags(effective, parents)
    atomic(DATA / 'plant_review_taxa.json', summary)
    atomic(out / 'taxonomy.json', summary)
    atomic(DATA / 'plant_review_tags.json', effective)
    atomic(out / 'index.json', {'image_ids': sorted(rows)})
    print(f'生成: {DIST / "plant_review.html"} / {len(rows)}画像。公開はしていません。')


def example():
    print(json.dumps({'schema_version': 1, 'image_id': '対象の画像ID', 'expected_revision': 0,
      'status': 'complete', 'reviewer': 'Codex', 'viewed_full_image': True,
      'image_notes': '全景と必要な拡大で手前・背景・端の対象を確認した内容。',
      'objects': [{'object_id': 'p1', 'bbox': [0.1, 0.2, 0.3, 0.5], 'scope': 'individual',
        'taxon': {'name': '分類名', 'scientific_name': '', 'rank': 'genus'},
        'certainty': 'confirmed', 'evidence': ['実際に見えた形質'],
        'limitations': 'より下位の分類に必要な特徴が見えない理由。',
        'diagnostic_comparison': '', 'candidates': [], 'morphology': [], 'sources': [],
        'qa_checked': False}]}, ensure_ascii=False, indent=2))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('next'); p.add_argument('--limit', type=int, default=120)
    p.add_argument('--include-screened', action='store_true', default=True)
    p.add_argument('--unseen-only', action='store_true')
    p = sub.add_parser('save'); p.add_argument('file')
    for name in ('stats', 'validate', 'build', 'example'):
        sub.add_parser(name)
    args = parser.parse_args()
    if args.command == 'next':
        next_images(args.limit, args.include_screened and not args.unseen_only)
    elif args.command == 'save':
        save(args.file)
    elif args.command == 'validate':
        idx, rows = index(), records()
        for r in rows.values():
            validate(r, idx, verify_image=True)
        print(f'検証OK: {len(rows)}画像（分類の正しさと矩形の対応は別途目視確認）')
    else:
        globals()[args.command]()


if __name__ == '__main__':
    main()
