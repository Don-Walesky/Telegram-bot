"""
Unit tests for StrategyLearningEngine dynamic hourly market harvester.
"""

import unittest
from unittest.mock import patch
from learning_engine import StrategyLearningEngine, DiscoveredMarket


class TestStrategyLearningEngine(unittest.TestCase):
    def test_get_learned_market_combinations(self):
        combos = StrategyLearningEngine.get_learned_market_combinations()
        self.assertGreaterEqual(len(combos), 3)
        self.assertTrue(any(c.combo_name == "Double Chance + Over 1.5 Goals" for c in combos))

    def test_learn_hourly_sportybet_markets(self):
        mock_catalog = [
            {
                "eventId": "sr:match:100",
                "markets": [
                    {
                        "id": "18",
                        "desc": "Over/Under Goals",
                        "outcomes": [{"desc": "Over 1.5"}, {"desc": "Under 1.5"}],
                    },
                    {
                        "id": "29",
                        "desc": "Asian Handicap (-0.5)",
                        "outcomes": [{"desc": "Home (-0.5)"}, {"desc": "Away (+0.5)"}],
                    },
                ],
            }
        ]

        with patch("sportybet_catalog.SportyBetCatalogService.fetch_sportybet_catalog", return_value=mock_catalog):
            res = StrategyLearningEngine.learn_hourly_sportybet_markets(sports=["Football"])
            self.assertGreaterEqual(res["total_indexed"], 2)
            self.assertGreaterEqual(res["new_this_hour"], 2)

            markets = StrategyLearningEngine.get_discovered_markets()
            self.assertIn("football:18", markets)
            self.assertEqual(markets["football:18"].market_name, "Over/Under Goals")
            self.assertIn("Over 1.5", markets["football:18"].outcomes)

            report = StrategyLearningEngine.format_learning_report()
            self.assertIn("SPORTYBET LIVE MARKET HARVESTER", report)
            self.assertIn("Over/Under Goals", report)


if __name__ == "__main__":
    unittest.main()
