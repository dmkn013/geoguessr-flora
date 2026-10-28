"""分類の細分化による集計漏れ・重複と不正な親参照を検証する。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from taxon_hierarchy import expand_tags, most_specific, parent_names, summarize_tags


class HierarchyTests(unittest.TestCase):
    def setUp(self):
        self.parents = {'変種A': '種A', '種A': '属A', '種B': '属A', '属A': '科A'}

    def test_variety_reaches_family_and_keeps_unrelated_tag(self):
        self.assertEqual(expand_tags(['変種A', '別科'], self.parents),
                         ['変種A', '別科', '種A', '属A', '科A'])
        self.assertEqual(most_specific(['科A', '属A', '変種A', '別科'], self.parents),
                         ['変種A', '別科'])

    def test_siblings_and_explicit_parent_count_each_image_once(self):
        result = summarize_tags({'1': ['種A', '種A', '種B', '科A'],
                                 '2': ['属A'], '3': []}, self.parents)
        self.assertEqual(result['inclusive_image_counts']['科A'], 2)
        self.assertEqual(result['inclusive_image_counts']['属A'], 2)
        self.assertEqual(result['direct_image_counts']['種A'], 1)
        self.assertEqual(result['reviewed_images'], 3)
        self.assertEqual(result['tagged_images'], 2)

    def test_catalog_overrides_legacy_shortcut_without_losing_other_tags(self):
        catalog = {'a': {'name': '種A', 'parent': 'b'},
                   'b': {'name': '属A', 'parent': 'c'}, 'c': {'name': '科A'}}
        parents = parent_names(catalog, {'種A': '科A', '旧種': '旧属'})
        self.assertEqual(expand_tags(['種A'], parents), ['種A', '属A', '科A'])
        self.assertEqual(parents['旧種'], '旧属')

    def test_invalid_parent_cycles_and_duplicate_names_rejected(self):
        for catalog in ({'a': {'name': 'A', 'parent': 'missing'}},
                        {'a': {'name': 'A', 'parent': 'b'}, 'b': {'name': 'B', 'parent': 'a'}},
                        {'a': {'name': 'A'}, 'b': {'name': 'A'}}):
            with self.subTest(catalog=catalog), self.assertRaises(ValueError):
                parent_names(catalog)


if __name__ == '__main__':
    unittest.main()
