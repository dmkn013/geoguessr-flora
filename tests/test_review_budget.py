import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from review_budget import recommend


class BudgetTests(unittest.TestCase):
    def test_limits_and_reset_observations(self):
        self.assertEqual(recommend(70, 0, 3, 100, [])['images'], 0)
        self.assertEqual(recommend(0, 80, 3, 100, [])['images'], 0)
        self.assertEqual(recommend(0, 0, 3, 100, [{'complete': 10, 'minutes': 5, 'start5': 90, 'end5': 0}])['images'], 4)

    def test_budget_accounts_for_future_runs_and_expensive_samples(self):
        observations = [{'complete': 10, 'minutes': 5, 'start5': 0, 'end5': 2}]
        fast = recommend(0, 0, 5, 168, observations)
        costly = recommend(0, 0, 5, 168, observations + [{'complete': 1, 'minutes': 2, 'start5': 0, 'end5': 5}])
        self.assertGreater(fast['images'], costly['images'])
        self.assertLessEqual(fast['images'] * fast['usage_points_per_image'], fast['usage_points_this_run'] + .001)
