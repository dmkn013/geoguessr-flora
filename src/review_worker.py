"""Mac等の分担端末向け。割当限定の画像取得・次画像・保存・検証。"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image
import plant_review as pr

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'plant-review-images-20261028'
REPOSITORY = 'dmkn013/geoguessr-flora'
BATCH_SIZE = 500


def configure(assignment_path):
    assignment = pr.load(assignment_path)
    if assignment.get('state') != 'reserved':
        raise ValueError('この割当は有効ではありません')
    worker = assignment['worker']
    aid = assignment['assignment_id']
    if any(not v or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in v)
           for v in (worker, aid)):
        raise ValueError('割当名に不正な文字があります')
    pr.RAW = ROOT / '.review-cache' / 'random'
    pr.RECORDS = ROOT / 'worker_results' / worker / aid
    ids = assignment['image_ids']
    pr.index = lambda: {i: {'img_id': i, 'file': i + '.jpg'} for i in ids}
    return assignment


def pending(assignment):
    done = pr.records()
    return [i for i in assignment['image_ids'] if i not in done or done[i]['status'] != 'complete']


def download(assignment, ids):
    all_ids = assignment['image_ids']
    positions = {i: n for n, i in enumerate(all_ids)}
    batches = sorted({positions[i] // BATCH_SIZE for i in ids if not (pr.RAW / (i + '.jpg')).exists()})
    downloads = ROOT / '.review-cache' / 'downloads'
    downloads.mkdir(parents=True, exist_ok=True)
    pr.RAW.mkdir(parents=True, exist_ok=True)
    for batch in batches:
        asset = f'brother-mac-{batch:03d}.zip'
        path = downloads / asset
        if not path.exists():
            subprocess.run(['gh', 'release', 'download', RELEASE, '--repo', REPOSITORY,
                            '--pattern', asset, '--dir', str(downloads)], check=True)
        allowed = set(all_ids[batch * BATCH_SIZE:(batch + 1) * BATCH_SIZE])
        with zipfile.ZipFile(path) as archive:
            names = {i + '.jpg' for i in allowed}
            if set(archive.namelist()) != names:
                raise ValueError(f'配布画像のID集合が不一致: {asset}')
            for name in archive.namelist():
                image_id = name[:-4]
                blob = archive.read(name)
                if hashlib.sha256(blob).hexdigest() != assignment['images'][image_id]['sha256']:
                    raise ValueError(f'配布画像のハッシュ不一致: {image_id}')
                target = pr.RAW / name
                if not target.exists():
                    tmp = target.with_suffix('.tmp')
                    tmp.write_bytes(blob)
                    os.replace(tmp, target)
        print(f'取得・ハッシュ検証OK: {asset}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assignment', type=Path,
                        default=ROOT / 'data/plant_review_assignments/brother-mac-20261028.json')
    sub = parser.add_subparsers(dest='command', required=True)
    nxt = sub.add_parser('next')
    nxt.add_argument('--limit', type=int, default=4)
    nxt.add_argument('--download', action='store_true')
    save = sub.add_parser('save')
    save.add_argument('file', type=Path)
    sub.add_parser('validate')
    sub.add_parser('stats')
    args = parser.parse_args()
    assignment = configure(args.assignment)
    if args.command == 'next':
        if not 1 <= args.limit <= 100:
            raise ValueError('limitは1〜100。目視は小バッチで進めてください')
        ids = pending(assignment)[:args.limit]
        if args.download:
            download(assignment, ids)
        for image_id in ids:
            path = pr.RAW / (image_id + '.jpg')
            if not path.exists():
                raise ValueError('画像が未取得です。next --downloadを実行してください')
            with Image.open(path) as im:
                size = list(im.size)
            done = pr.load(pr.RECORDS / (image_id + '.json'), {})
            print(json.dumps({'image_id': image_id, 'path': str(path), 'size': size,
                              'expected_revision': done.get('revision', 0)}, ensure_ascii=False))
    elif args.command == 'save':
        record = pr.load(args.file)
        image_id = record.get('image_id')
        if image_id not in assignment['images']:
            raise ValueError('割当外の画像は保存できません')
        source = pr.RAW / (image_id + '.jpg')
        if hashlib.sha256(source.read_bytes()).hexdigest() != assignment['images'][image_id]['sha256']:
            raise ValueError('原画像ハッシュ不一致')
        if record.get('status') == 'complete' and any(o.get('qa_checked') is not True for o in record.get('objects', [])):
            raise ValueError('completeの前に全矩形を実視認してQAしてください')
        record['assignment_id'] = assignment['assignment_id']
        record['reviewer'] = 'Codex-brother-mac'
        scratch = ROOT / '.review-cache' / 'save-input.json'
        scratch.parent.mkdir(parents=True, exist_ok=True)
        scratch.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        pr.save(scratch)
    elif args.command == 'validate':
        records = pr.records()
        for record in records.values():
            pr.validate(record, pr.index(), verify_image=True)
            if record['status'] == 'complete' and any(o.get('qa_checked') is not True for o in record['objects']):
                raise ValueError('完了記録に未QAの矩形があります')
        print(f'検証OK: {len(records)}枚。分類と矩形対応は別途目視確認が必要です')
    else:
        records = pr.records()
        complete = sum(r['status'] == 'complete' for r in records.values())
        print(json.dumps({'assigned': len(assignment['image_ids']), 'complete': complete,
                          'screened_only': len(records) - complete,
                          'remaining': len(assignment['image_ids']) - complete}, ensure_ascii=False))


if __name__ == '__main__':
    main()
