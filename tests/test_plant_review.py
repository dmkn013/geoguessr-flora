"""元画像との対応・矩形・種以下の根拠・履歴保存を検証する。"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import plant_review as review


def record():
    return {'schema_version': 1, 'image_id': 'sample', 'status': 'complete',
            'reviewer': 'test', 'viewed_full_image': True, 'image_notes': '全景確認済み',
            'objects': [{'object_id': 'p1', 'bbox': [0.1, 0.2, 0.3, 0.4],
                         'scope': 'individual', 'taxon': {'name': 'マツ属', 'rank': 'genus'},
                         'certainty': 'confirmed', 'evidence': ['針葉が枝先に集まる'],
                         'limitations': '針葉の束の本数が不明', 'candidates': [],
                         'morphology': [], 'sources': [], 'qa_checked': False}]}


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.idx = {'sample': {'file': 'sample.jpg'}}

    def test_bad_boxes(self):
        for box in ([0, 0, 0, 1], [-0.1, 0, 1, 1], [0.9, 0, 0.2, 1], [0, 0, float('nan'), 1], [False, 0, 1, 1]):
            r = record(); r['objects'][0]['bbox'] = box
            with self.subTest(box=box), self.assertRaises(ValueError):
                review.validate(r, self.idx)

    def test_multiple_objects_and_duplicate_ids(self):
        r = record(); obj = copy.deepcopy(r['objects'][0]); obj['object_id'] = 'p2'
        r['objects'].append(obj)
        review.validate(r, self.idx)
        obj['object_id'] = 'p1'
        with self.assertRaises(ValueError): review.validate(r, self.idx)

    def test_species_requires_diagnostics_and_source(self):
        r = record(); o = r['objects'][0]
        o['taxon'] = {'name': '架空の種', 'rank': 'species', 'scientific_name': 'Example test'}
        with self.assertRaises(ValueError): review.validate(r, self.idx)
        o['diagnostic_comparison'] = '類似種との差を実際に確認'
        o['sources'] = [{'url': 'https://example.org/flora', 'supports': '識別形質の記載'}]
        review.validate(r, self.idx)

    def test_unviewed_image_rejected(self):
        r = record(); r['viewed_full_image'] = False
        with self.assertRaises(ValueError): review.validate(r, self.idx)

    def test_empty_requires_reason(self):
        r = record(); r['objects'] = []
        with self.assertRaises(ValueError): review.validate(r, self.idx)
        r['empty_reason'] = 'not_identifiable'
        review.validate(r, self.idx)

    def test_location_label_is_not_exported_as_taxon_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new('RGB', (100, 80)).save(root / 'sample.jpg')
            (root / 'taxon_catalog.json').write_text(json.dumps({'Pinus': {'name': 'マツ属', 'rank': 'genus'}}), encoding='utf-8')
            r = record()
            r['objects'][0]['taxon'].update(name='右側のマツ属', scientific_name='Pinus')
            inp = root / 'input.json'
            inp.write_text(json.dumps(r), encoding='utf-8')
            with patch.object(review, 'RAW', root), patch.object(review, 'DATA', root), patch.object(review, 'RECORDS', root / 'records'), patch.object(review, 'index', return_value=self.idx):
                review.save(inp)
                saved = review.load(root / 'records/sample.json')['objects'][0]
                self.assertEqual(saved['taxon']['name'], 'マツ属')
                self.assertEqual(saved['label'], '右側のマツ属')
                r['objects'][0]['taxon']['rank'] = 'species'
                inp.write_text(json.dumps(r), encoding='utf-8')
                with self.assertRaises(ValueError):
                    review.save(inp)

    def test_build_counts_only_complete_qa_ready_confirmed_taxa(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); raw = root / 'raw'; raw.mkdir()
            catalog = {'Example': {'name': '属A', 'rank': 'genus', 'parent': 'Family'},
                       'Family': {'name': '科A', 'rank': 'family'},
                       'Example test': {'name': '種A', 'rank': 'species', 'parent': 'Example'}}
            review.atomic(root / 'taxon_catalog.json', catalog)
            idx = {i: {'file': i + '.jpg'} for i in ('sample', 'screened', 'pending', 'mixed')}
            with patch.object(review, 'RAW', raw), patch.object(review, 'DATA', root), patch.object(review, 'DIST', root / 'dist'), patch.object(review, 'RECORDS', root / 'records'), patch.object(review, 'index', return_value=idx):
                for iid in idx:
                    Image.new('RGB', (100, 80)).save(raw / (iid + '.jpg'))
                    r = record(); r['image_id'] = iid
                    o = r['objects'][0]
                    o['taxon'] = {'name': '種A', 'rank': 'species', 'scientific_name': 'Example test'}
                    o['diagnostic_comparison'] = '診断形質を比較'
                    o['sources'] = [{'url': 'https://example.org/flora', 'supports': '診断形質'}]
                    o['qa_checked'] = iid != 'pending'
                    if iid == 'screened':
                        r['status'] = 'screened'
                    elif iid == 'sample':
                        other = copy.deepcopy(o); other['object_id'] = 'p2'
                        r['objects'].append(other)
                    elif iid == 'mixed':
                        o['certainty'] = 'provisional'
                        other = copy.deepcopy(o); other['object_id'] = 'p2'
                        other['certainty'] = 'confirmed'
                        other['taxon'] = {'name': '属A', 'rank': 'genus', 'scientific_name': 'Example'}
                        r['objects'].append(other)
                    inp = root / 'input.json'; review.atomic(inp, r); review.save(inp)
                review.build()
                tags = review.load(root / 'plant_review_tags.json')
                self.assertEqual(tags, {'sample': ['種A'], 'mixed': ['属A']})
                summary = review.load(root / 'plant_review_taxa.json')
                self.assertEqual(summary['inclusive_image_counts'], {'属A': 2, '科A': 2, '種A': 1})
                self.assertEqual(summary, review.load(root / 'dist/plant_reviews/taxonomy.json'))

    def test_revision_history_conflict_and_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); raw = root / 'raw'; raw.mkdir()
            Image.new('RGB', (100, 80)).save(raw / 'sample.jpg')
            inp = root / 'input.json'; inp.write_text(json.dumps(record()), encoding='utf-8')
            with patch.object(review, 'RAW', raw), patch.object(review, 'RECORDS', root / 'records'), patch.object(review, 'index', return_value=self.idx):
                review.save(inp)
                stored = review.load(root / 'records/sample.json')
                self.assertEqual(stored['source_size'], [100, 80])
                with self.assertRaises(ValueError): review.save(inp)
                r = record(); r['expected_revision'] = 1
                inp.write_text(json.dumps(r), encoding='utf-8'); review.save(inp)
                self.assertTrue((root / 'records/history/sample-1.json').exists())
                Image.new('RGB', (100, 80), 'red').save(raw / 'sample.jpg')
                with self.assertRaises(ValueError): review.validate(stored, self.idx, verify_image=True)


if __name__ == '__main__':
    unittest.main()
