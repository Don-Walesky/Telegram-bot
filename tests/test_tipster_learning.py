import unittest
from tipster_learning import TipsterMarketLearner
from database import DatabaseService


class TestTipsterMarketLearner(unittest.TestCase):
    def setUp(self):
        DatabaseService.init_db()

    def test_analyze_channel_post(self):
        sample_post = "Bet9ja Code B9JA99: Chelsea vs Arsenal (1X), Real Madrid (Over 1.5), Lakers (Moneyline)"
        learned_markets = TipsterMarketLearner.analyze_channel_post(sample_post, sport_hint="Football")

        self.assertIn("Double Chance (1X/X2)", learned_markets)
        self.assertIn("Over 1.5 Goals", learned_markets)

    def test_get_tipster_market_summary(self):
        TipsterMarketLearner.analyze_channel_post("Barcelona (Double Chance 1X)")
        summary = TipsterMarketLearner.get_tipster_market_summary(limit=5)

        self.assertTrue(len(summary) > 0)
        self.assertIsNotNone(summary[0].market_name)
        self.assertGreater(summary[0].popularity_percentage, 0.0)

    def test_format_tipster_learning_report(self):
        report = TipsterMarketLearner.format_tipster_learning_report()
        self.assertIn("WATCHED TELEGRAM CHANNELS", report)
        self.assertIn("TIPSTER MARKET INSIGHTS", report)


if __name__ == "__main__":
    unittest.main()
