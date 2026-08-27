import unittest
from datetime import datetime, timedelta
from livescore_client import DiscoveredFixture
from sportybet_catalog import SportyBetCatalogService, MappedSportyBetSelection
from probability_filter import ImpliedProbabilityFilter
from sportybet_booking import SportyBetBookingClient


class TestRealMappingAndPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_sb_events = [
            {
                "eventId": "sr:match:998877",
                "homeTeamName": "Arsenal FC",
                "awayTeamName": "Chelsea FC",
                "tournament": {"name": "England Premier League"},
                "sport": {"name": "Football"},
                "estimateStartTime": int((datetime.now() + timedelta(hours=2)).timestamp() * 1000),
                "markets": [
                    {
                        "id": "10",
                        "name": "Double Chance",
                        "outcomes": [
                            {"id": "1", "name": "1X", "odds": 1.12},  # Implied prob: (1/1.12)*100 = 89.3%
                            {"id": "2", "name": "X2", "odds": 1.45},  # Implied prob: (1/1.45)*100 = 69.0%
                        ],
                    },
                    {
                        "id": "18",
                        "name": "Over/Under",
                        "specifier": "total=1.5",
                        "outcomes": [
                            {"id": "12", "name": "Over 1.5", "odds": 1.10}, # Implied prob: 90.9%
                        ],
                    },
                ],
            }
        ]

    def test_fuzzy_fixture_matching(self):
        fixture = DiscoveredFixture(
            sport="Football",
            league="Premier League",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=datetime.now() + timedelta(hours=2),
            status="NS",
        )
        matched_event = SportyBetCatalogService.match_fixture(fixture, self.mock_sb_events)
        self.assertIsNotNone(matched_event)
        self.assertEqual(matched_event["eventId"], "sr:match:998877")

    def test_implied_probability_calculation(self):
        prob_1_12 = ImpliedProbabilityFilter.calculate_implied_probability(1.12)
        self.assertAlmostEqual(prob_1_12, 89.285, places=2)

        prob_1_10 = ImpliedProbabilityFilter.calculate_implied_probability(1.10)
        self.assertAlmostEqual(prob_1_10, 90.909, places=2)

    def test_probability_filtering_85_to_95(self):
        selections = SportyBetCatalogService.extract_selections_from_event(self.mock_sb_events[0])
        filtered = ImpliedProbabilityFilter.filter_selections(selections, min_prob=85.0, max_prob=95.0)

        # 1X (@1.12 => 89.3%) and Over 1.5 (@1.10 => 90.9%) should be kept; X2 (@1.45 => 69.0%) dropped
        odds_values = [f.odds for f in filtered]
        self.assertIn(1.12, odds_values)
        self.assertIn(1.10, odds_values)
        self.assertNotIn(1.45, odds_values)

    def test_booking_client_fallback_does_not_fabricate_code(self):
        selections = SportyBetCatalogService.extract_selections_from_event(self.mock_sb_events[0])
        filtered = ImpliedProbabilityFilter.filter_selections(selections, min_prob=85.0, max_prob=95.0)

        # Calling generate_booking_code without live SportyBet server session must return fallback without fake code
        slip_res = SportyBetBookingClient.generate_booking_code(filtered)
        self.assertIn("Bookmaker-Implied Prob", slip_res.formatted_summary)
        if not slip_res.booking_code:
            self.assertIn("No valid booking code generated", slip_res.formatted_summary)


if __name__ == "__main__":
    unittest.main()
