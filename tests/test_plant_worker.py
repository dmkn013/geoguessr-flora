"""分担画像の二重処理と取り込み時の原画像取り違えを防ぐ。"""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import plant_review as pr
import import_plant_worker as worker


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / 'data'
        self.data.mkdir()
        self.records = self.data / 'plant_reviews'
        self.records.mkdir()
        self.returned = self.root / 'returned'
        self.returned.mkdir()
        self.raw = self.root / 'random'
        self.raw.mkdir()
        self.idx = {i: {'img_id': i, 'file': i + '.jpg'} for i in ['reserved', 'free']}
        for i in self.idx:
            Image.new('RGB', (10, 10), 'green').save(self.raw / (i + '.jpg'))
        self.digest = hashlib.sha256((self.raw / 'reserved.jpg').read_bytes()).hexdigest()
        for name, value in [('random_index.json', list(self.idx.values())), ('tags.json', {}), ('taxon_catalog.json', {})]:
            (self.data / name).write_text(json.dumps(value), encoding='utf-8')
        assignments = self.data / 'plant_review_assignments'
        assignments.mkdir()
        self.assignment = assignments / 'pilot.json'
        self.assignment.write_text(json.dumps({'state': 'reserved', 'assignment_id': 'pilot', 'worker': 'souka',
                                              'image_ids': ['reserved'], 'images': {'reserved': {'sha256': self.digest}}}), encoding='utf-8')
        self.record = {'schema_version': 1, 'image_id': 'reserved', 'status': 'complete',
                       'reviewer': 'test', 'viewed_full_image': True, 'image_notes': '全景に植物なし',
                       'objects': [], 'empty_reason': 'no_visible_plants',
                       'source_sha256': self.digest, 'source_size': [10, 10]}
        self.return_path = self.returned / 'reserved.json'
        self.write_record()
        for key, value in [('DATA', self.data), ('RECORDS', self.records), ('RAW', self.raw)]:
            p = patch.object(pr, key, value)
            p.start()
            self.addCleanup(p.stop)

    def write_record(self):
        self.return_path.write_text(json.dumps(self.record), encoding='utf-8')

    def test_next_excludes_reserved_and_accepts_return_without_writes(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            pr.next_images(10)
        self.assertEqual([json.loads(s)['image_id'] for s in output.getvalue().splitlines()], ['free'])
        _, records = worker.preflight(self.returned, self.assignment)
        self.assertEqual(len(records), 1)
        self.assertEqual(list(self.records.iterdir()), [])

    def test_rejects_changed_image_and_existing_result(self):
        (self.raw / 'reserved.jpg').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'ハッシュ不一致'):
            worker.preflight(self.returned, self.assignment)
        (self.records / 'reserved.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, '既存記録'):
            worker.preflight(self.returned, self.assignment)

    def test_rejects_foreign_id_and_unchecked_object(self):
        self.record['image_id'] = 'free'
        self.write_record()
        with self.assertRaisesRegex(ValueError, '割当外'):
            worker.preflight(self.returned, self.assignment)
        self.record['image_id'] = 'reserved'
        self.record['objects'] = [{'qa_checked': False}]
        self.write_record()
        with self.assertRaisesRegex(ValueError, '矩形QA'):
            worker.preflight(self.returned, self.assignment)


if __name__ == '__main__':
    unittest.main()
