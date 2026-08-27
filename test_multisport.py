import unittest
from aggregator import PredictionAggregator
from analyzer import PredictionAnalyzer
from builder import CustomSlipBuilder


class TestMultiSportAndDateEngine(unittest.TestCase):
    def test_today_all_sports(self):
        preds = PredictionAggregator.get_all_raw_predictions(match_date="Today", sport="All")
        self.assertGreater(len(preds), 0)
        sports = set(p.sport for p in preds)
        self.assertIn("Football", sports)
        self.assertIn("Basketball", sports)

    def test_tomorrow_football(self):
        preds = PredictionAggregator.get_all_raw_predictions(match_date="Tomorrow", sport="Football")
        self.assertGreater(len(preds), 0)
        for p in preds:
            self.assertEqual(p.match_date, "Tomorrow")
            self.assertEqual(p.sport, "Football")

    def test_custom_slip_multisport(self):
        res = CustomSlipBuilder.generate_custom_slip(
            target_odds=2.0, game_count=3, min_probability=85.0, match_date="Today", sport="All"
        )
        self.assertIn("MULTI-SPORT PREDICTION SLIP", res.formatted_summary)
        self.assertIn("TODAY", res.formatted_summary)


if __name__ == "__main__":
    unittest.main()
