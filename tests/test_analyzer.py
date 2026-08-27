import unittest
from aggregator import PredictionAggregator, RawPrediction
from analyzer import PredictionAnalyzer, SafeMarketPrediction


class TestConsensusAnalyzer(unittest.TestCase):
    def test_market_conversion_to_safe(self):
        pick_1, odds_1 = PredictionAnalyzer.convert_to_ultra_safe_market("1")
        self.assertIn("1X", pick_1)
        self.assertGreater(odds_1, 1.0)

        pick_over, odds_over = PredictionAnalyzer.convert_to_ultra_safe_market("Over 2.5")
        self.assertIn("Over 1.5 Goals", pick_over)

    def test_consensus_analysis(self):
        results = PredictionAnalyzer.analyze_high_probability_fixtures(target_threshold=90.0)
        self.assertIsInstance(results, list)
        if results:
            first_pick = results[0]
            self.assertGreaterEqual(first_pick.consensus_score, 90.0)

    def test_report_formatting(self):
        report = PredictionAnalyzer.format_consensus_report()
        self.assertIn("HIGH-PROBABILITY MULTI-SPORT PREDICTIONS", report)


if __name__ == "__main__":
    unittest.main()
