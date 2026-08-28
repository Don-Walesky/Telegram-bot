import unittest
from unittest.mock import patch, MagicMock
from betting_service import BettingService
from livescore_client import DiscoveredFixture
from sportybet_catalog import MappedSportyBetSelection
from probability_filter import FilteredPick
from sportybet_booking import BookingSlipResponse
from config import config
from datetime import datetime, timedelta


class TestBettingService(unittest.TestCase):
    @patch("betting_service.LiveScoreClient.fetch_unstarted_fixtures")
    def test_empty_fixtures_handling(self, mock_fetch):
        mock_fetch.return_value = []
        res = BettingService.execute_scan_pipeline("Today", "Football")
        self.assertFalse(res.success)
        self.assertIsNone(res.booking_code)
        self.assertIn("No unstarted matches", res.formatted_summary)

    @patch("betting_service.LiveScoreClient.fetch_unstarted_fixtures")
    @patch("betting_service.SportyBetCatalogService.fetch_sportybet_catalog")
    def test_empty_catalog_handling(self, mock_sb_catalog, mock_fetch_fixtures):
        mock_fetch_fixtures.return_value = [
            DiscoveredFixture(
                sport="Football",
                league="Premier League",
                home_team="Arsenal",
                away_team="Chelsea",
                kickoff_time=datetime.now() + timedelta(hours=2),
                status="NS",
            )
        ]
        mock_sb_catalog.return_value = []

        res = BettingService.execute_scan_pipeline("Today", "Football")
        self.assertFalse(res.success)
        self.assertTrue(res.unmapped_warning)
        self.assertIn("Catalog Status Update", res.formatted_summary)

    @patch("betting_service.LiveScoreClient.fetch_unstarted_fixtures")
    @patch("betting_service.SportyBetCatalogService.fetch_sportybet_catalog")
    @patch("betting_service.SportyBetCatalogService.match_fixture")
    @patch("betting_service.SportyBetCatalogService.extract_selections_from_event")
    @patch("betting_service.SportyBetBookingClient.generate_booking_code")
    def test_successful_pipeline_execution(
        self, mock_gen_code, mock_extract, mock_match, mock_sb_catalog, mock_fetch_fixtures
    ):
        fix = DiscoveredFixture(
            sport="Football",
            league="Premier League",
            home_team="Arsenal",
            away_team="Chelsea",
            kickoff_time=datetime.now() + timedelta(hours=2),
            status="NS",
        )
        mock_fetch_fixtures.return_value = [fix]
        mock_sb_catalog.return_value = [{"id": "sr:match:101"}]
        mock_match.return_value = {"id": "sr:match:101"}

        selection = MappedSportyBetSelection(
            event_id="sr:match:101",
            home_team="Arsenal",
            away_team="Chelsea",
            league="Premier League",
            sport="Football",
            kickoff_time=datetime.now() + timedelta(hours=2),
            market_id="18",
            market_name="Double Chance",
            outcome_id="12",
            outcome_name="1X",
            odds=1.18,
        )
        mock_extract.return_value = [selection]

        expected_response = BookingSlipResponse(
            success=True,
            booking_code="REALBC101",
            share_url="https://www.sportybet.com/ng/?shareCode=REALBC101",
            picks=[],
            total_odds=1.18,
            formatted_summary="Mock Slip Summary",
        )
        mock_gen_code.return_value = expected_response

        res = BettingService.execute_scan_pipeline("Today", "Football")
        self.assertTrue(res.success)
        self.assertEqual(res.booking_code, "REALBC101")
        mock_gen_code.assert_called_once()
        picks_sent = mock_gen_code.call_args[0][0]
        self.assertLessEqual(len(picks_sent), config.betting.default_scan_legs)


if __name__ == "__main__":
    unittest.main()
