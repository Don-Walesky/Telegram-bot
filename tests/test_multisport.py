import unittest
from datetime import datetime
from aggregator import PredictionAggregator, RawPrediction
from analyzer import PredictionAnalyzer, ConsensusPrediction
from builder import CustomSlipBuilder, CustomSlipResult


class TestMultiSportAndDateEngine(unittest.TestCase):
    def test_aggregator_multi_sport_date_filtering(self):
        # Fetch today's football fixtures
        today_football = PredictionAggregator.get_upcoming_fixtures(match_date="Today", sport="Football")
        self.assertIsInstance(today_football, list)
        for item in today_football:
            self.assertIsInstance(item, RawPrediction)
            self.assertEqual(item.sport, "Football")
            self.assertEqual(item.match_date, "Today")

        # Fetch tomorrow's all-sports fixtures
        tomorrow_all = PredictionAggregator.get_upcoming_fixtures(match_date="Tomorrow", sport="All")
        self.assertIsInstance(tomorrow_all, list)
        for item in tomorrow_all:
            self.assertIsInstance(item, RawPrediction)
            self.assertEqual(item.match_date, "Tomorrow")

    def test_analyzer_safe_market_conversions(self):
        # Football safe market conversion
        market_fb, odds_fb = PredictionAnalyzer.convert_to_safe_market("1", "Football")
        self.assertEqual(market_fb, "Double Chance (1X)")
        self.assertGreater(odds_fb, 1.0)

        # Basketball safe market conversion
        market_bb, odds_bb = PredictionAnalyzer.convert_to_safe_market("1", "Basketball")
        self.assertEqual(market_bb, "Winner (2-Way Incl. OT)")
        self.assertGreater(odds_bb, 1.0)

        # Tennis safe market conversion
        market_tn, odds_tn = PredictionAnalyzer.convert_to_safe_market("Winner", "Tennis")
        self.assertIn("Match Winner", market_tn)
        self.assertGreater(odds_tn, 1.0)

        # Ice Hockey safe market conversion
        market_hk, odds_hk = PredictionAnalyzer.convert_to_safe_market("1", "Ice Hockey")
        self.assertEqual(market_hk, "Double Chance (1X)")
        self.assertGreater(odds_hk, 1.0)

    def test_custom_slip_builder_date_and_sport(self):
        res = CustomSlipBuilder.generate_custom_slip(
            target_odds=2.5,
            game_count=3,
            min_probability=60.0,
            match_date="Today",
            sport="Football",
        )
        self.assertIsInstance(res, CustomSlipResult)
        self.assertGreaterEqual(res.actual_odds, 0.0)
        self.assertIn("CUSTOM MULTI-SPORT PREDICTION SLIP", res.formatted_summary)
        self.assertIn("FOOTBALL", res.formatted_summary)
        self.assertIn("TODAY", res.formatted_summary)


    def test_livescore_unstarted_filter(self):
        from livescore_client import is_unstarted_match
        self.assertTrue(is_unstarted_match("NS"))
        self.assertTrue(is_unstarted_match("Sched"))
        self.assertTrue(is_unstarted_match("20:00"))
        self.assertTrue(is_unstarted_match("19:45"))

        self.assertFalse(is_unstarted_match("FT"))
        self.assertFalse(is_unstarted_match("HT"))
        self.assertFalse(is_unstarted_match("63'"))
        self.assertFalse(is_unstarted_match("CANC"))
        self.assertFalse(is_unstarted_match("ABD"))


if __name__ == "__main__":
    unittest.main()
