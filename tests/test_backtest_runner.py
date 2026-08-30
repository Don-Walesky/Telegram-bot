"""
Unit Tests for Historical Backtesting Runner Module
"""

import unittest
from engine.backtest_runner import BacktestRunner


class TestBacktestRunner(unittest.TestCase):
    def test_evaluate_selection_outcome_double_chance(self):
        # 1X on 2-1 (Home win) -> True
        self.assertTrue(BacktestRunner.evaluate_selection_outcome("Double Chance", "1X", 2, 1))
        # 1X on 1-1 (Draw) -> True
        self.assertTrue(BacktestRunner.evaluate_selection_outcome("Double Chance", "1X", 1, 1))
        # 1X on 0-2 (Away win) -> False
        self.assertFalse(BacktestRunner.evaluate_selection_outcome("Double Chance", "1X", 0, 2))

    def test_evaluate_selection_outcome_over_under(self):
        # Over 1.5 on 2-0 (2 goals) -> True
        self.assertTrue(BacktestRunner.evaluate_selection_outcome("Over 1.5 Goals", "Over 1.5", 2, 0))
        # Over 1.5 on 1-0 (1 goal) -> False
        self.assertFalse(BacktestRunner.evaluate_selection_outcome("Over 1.5 Goals", "Over 1.5", 1, 0))
        # Over 2.5 on 2-1 (3 goals) -> True
        self.assertTrue(BacktestRunner.evaluate_selection_outcome("Over 2.5 Goals", "Over 2.5", 2, 1))

    def test_evaluate_selection_outcome_1x2(self):
        # 1X2 Home Win on 3-1 -> True
        self.assertTrue(BacktestRunner.evaluate_selection_outcome("1X2", "Home Win", 3, 1))
        # 1X2 Away Win on 1-2 -> True
        self.assertTrue(BacktestRunner.evaluate_selection_outcome("1X2", "Away Win", 1, 2))
        # 1X2 Draw on 2-2 -> True
        self.assertTrue(BacktestRunner.evaluate_selection_outcome("1X2", "Draw", 2, 2))

    def test_run_backtest_simulation(self):
        simulated_slips = [
            {
                "request_id": "slip_1",
                "stake": 1000.0,
                "legs": [
                    {
                        "candidate_id": "c1",
                        "event_id": "e1",
                        "fixture": "Arsenal vs Chelsea",
                        "market_name": "Double Chance",
                        "outcome_name": "1X",
                        "odds": 1.20,
                        "model_probability": 0.85,
                    },
                    {
                        "candidate_id": "c2",
                        "event_id": "e2",
                        "fixture": "Liverpool vs Everton",
                        "market_name": "Over 1.5 Goals",
                        "outcome_name": "Over 1.5",
                        "odds": 1.25,
                        "model_probability": 0.80,
                    },
                ],
            }
        ]

        settlements = {
            "e1": {"home_score": 2, "away_score": 1},
            "e2": {"home_score": 3, "away_score": 0},
        }

        report = BacktestRunner.run_backtest(simulated_slips, settlements)

        self.assertEqual(report.total_slips, 1)
        self.assertEqual(report.won_slips, 1)
        self.assertEqual(report.slip_win_rate_pct, 100.0)
        self.assertEqual(report.total_legs, 2)
        self.assertEqual(report.won_legs, 2)
        self.assertEqual(report.leg_hit_rate_pct, 100.0)
        # 1.20 * 1.25 = 1.50 -> 1000 stake -> 1500 payout -> 500 profit (50% ROI)
        self.assertAlmostEqual(report.roi_pct, 50.0, places=1)
        # Brier loss = ((0.85 - 1)^2 + (0.80 - 1)^2)/2 = (0.0225 + 0.04) / 2 = 0.03125
        self.assertAlmostEqual(report.mean_brier_score, 0.0313, places=3)


if __name__ == "__main__":
    unittest.main()
