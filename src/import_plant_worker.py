"""分担結果を検査し、明示的な --apply 時だけ中央記録へ取り込む。"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import plant_review as pr


def preflight(folder, assignment):
    manifest = pr.load(assignment)
    if manifest.get('state') != 'reserved':
        raise ValueError('予約中の割当ではありません')
    allowed = set(manifest['image_ids'])
    idx = pr.index()
    catalog = pr.load(pr.DATA / 'taxon_catalog.json', {})
    records = []
    for path in sorted(Path(folder).glob('*.json')):
        record = pr.load(path)
        image_id = record.get('image_id')
        if image_id not in allowed or path.stem != image_id:
            raise ValueError(f'割当外またはファイル名不一致: {path.name}')
        if (pr.RECORDS / path.name).exists():
            raise ValueError(f'中央に既存記録があります。上書きせず個別確認: {image_id}')
        if record.get('status') != 'complete' or any(
                o.get('qa_checked') is not True for o in record.get('objects', [])):
            raise ValueError(f'完了・矩形QAが不足: {image_id}')
        if record.get('source_sha256') != manifest['images'][image_id]['sha256']:
            raise ValueError(f'割当時のハッシュと不一致: {image_id}')
        pr.validate(record, idx, verify_image=True)
        for obj in record['objects']:
            taxon = obj['taxon']
            if taxon['rank'] != 'unknown':
                entry = catalog.get(taxon.get('scientific_name'))
                if not entry or entry['rank'] != taxon['rank'] or entry['name'] != taxon['name']:
                    raise ValueError(f'中央辞書で分類の承認が必要: {image_id} {taxon}')
        records.append(record)
    if not records:
        raise ValueError('取り込み対象がありません')
    return manifest, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records', type=Path, help='返却された data/plant_reviews フォルダ')
    parser.add_argument('--assignment', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    manifest, records = preflight(args.records, args.assignment)
    print(f'事前検査OK: {len(records)}枚 / {manifest["assignment_id"]}')
    print('分類・矩形の正しさは中央で別途画像と照合してください')
    if not args.apply:
        print('検査のみ。中央の記録は変更していません')
        return
    # 全件の事前検査後に保存。中断時も既存記録を上書きせず再検査で停止する。
    scratch = pr.DIST / 'review_work' / 'worker_import'
    scratch.mkdir(parents=True, exist_ok=True)
    for original in records:
        record = copy.deepcopy(original)
        record['worker_reviewed_at'] = record.pop('reviewed_at', None)
        record.pop('revision', None)
        record['expected_revision'] = 0
        record['assignment_id'] = manifest['assignment_id']
        record['reviewer'] = f'{original["reviewer"]} / {manifest["worker"]}'
        record['worker_record_sha256'] = hashlib.sha256(
            (args.records / f'{record["image_id"]}.json').read_bytes()).hexdigest()
        path = scratch / f'{record["image_id"]}.json'
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        pr.save(path)
    # 部分返却でも残りの割当を保持する。再実行は未取り込み分だけを別フォルダへ。
    manifest['imported_image_ids'] = sorted(set(manifest.get('imported_image_ids', [])) |
                                            {r['image_id'] for r in records})
    if set(manifest['imported_image_ids']) == set(manifest['image_ids']):
        manifest['state'] = 'completed'
    pr.atomic(args.assignment, manifest)
    print('取り込み完了。元の返却一式と履歴は保管してください')


if __name__ == '__main__':
    main()
