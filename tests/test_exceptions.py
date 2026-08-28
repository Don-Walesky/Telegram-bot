import unittest
from exceptions import (
    BotError,
    ExternalAPIError,
    LiveScoreAPIError,
    SportyBetAPIError,
    BetCodeConversionError,
    DatabaseError,
    ValidationError,
)


class TestExceptions(unittest.TestCase):
    def test_bot_error_hierarchy(self):
        err = LiveScoreAPIError("Failed to fetch fixtures", details="Timeout 8.0s")
        self.assertIsInstance(err, BotError)
        self.assertIsInstance(err, ExternalAPIError)
        self.assertEqual(err.provider, "LiveScore")
        self.assertIn("Failed to fetch fixtures", str(err))
        self.assertIn("Timeout 8.0s", str(err))

    def test_sportybet_api_error(self):
        err = SportyBetAPIError("Share API HTTP Error", status_code=500, details="Internal Server Error")
        self.assertIsInstance(err, ExternalAPIError)
        self.assertEqual(err.provider, "SportyBet")
        self.assertEqual(err.status_code, 500)

    def test_database_error(self):
        err = DatabaseError("Disk full", query="INSERT INTO slips")
        self.assertIsInstance(err, BotError)
        self.assertEqual(err.query, "INSERT INTO slips")

    def test_validation_error(self):
        err = ValidationError("Odds outside target range", field_name="target_odds")
        self.assertIsInstance(err, BotError)
        self.assertEqual(err.field_name, "target_odds")


if __name__ == "__main__":
    unittest.main()
