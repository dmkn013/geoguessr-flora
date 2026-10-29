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

    def test_budget_obeys_remaining_capacity_and_expensive_samples(self):
        observations = [{'complete': 10, 'minutes': 5, 'start5': 0, 'end5': 2, 'start_weekly': 0, 'end_weekly': 1}]
        fast = recommend(60, 0, 5, 168, observations)
        costly = recommend(60, 0, 5, 168, observations + [{'complete': 1, 'minutes': 2, 'start5': 0, 'end5': 5}])
        self.assertGreater(fast['images'], costly['images'])
        self.assertLessEqual(fast['images'] * fast['usage_points_per_image'], fast['usage_points_this_run'] + .001)
        self.assertLessEqual(fast['images'] * fast['weekly_points_per_image'], fast['weekly_points_this_run'] + .001)
        self.assertGreater(fast['weekly_points_per_image'], 0)
        rounded = recommend(0, 0, 5, 168, observations + [{'complete': 1, 'minutes': 1, 'start5': 0, 'end5': 1, 'start_weekly': 1, 'end_weekly': 1}])
        self.assertEqual(rounded['weekly_points_per_image'], fast['weekly_points_per_image'])

    def test_no_hourly_allocation_or_carry_wait(self):
        observations = [{'complete': 1, 'minutes': 2, 'start5': 0, 'end5': 3, 'start_weekly': 0, 'end_weekly': 1}]
        immediate = recommend(2, 6, 4, 163, observations)
        self.assertEqual(immediate['images'], 4)
        self.assertEqual(immediate, recommend(2, 6, 1, 2, observations, idle_hours=24))
        self.assertEqual(recommend(70, 6, 4, 163, observations)['images'], 0)
        self.assertEqual(recommend(2, 80, 4, 163, observations)['images'], 0)
        near_limit = recommend(69, 79, 4, 163, observations)
        self.assertEqual(near_limit['images'], 0)
