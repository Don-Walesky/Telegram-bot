import unittest
from database import DatabaseService


class TestDatabaseService(unittest.TestCase):
    def setUp(self):
        DatabaseService.init_db()

    def test_save_and_retrieve_history(self):
        user_id = 99887766
        row_id = DatabaseService.save_slip(
            user_id=user_id,
            match_date="Today",
            sport="Football",
            game_count=3,
            target_odds=2.5,
            actual_odds=2.3,
            min_probability=75.0,
            booking_code="BC9910",
            summary_text="Test Summary",
        )
        self.assertGreater(row_id, 0)

        history = DatabaseService.get_user_history(user_id=user_id, limit=5)
        self.assertTrue(len(history) > 0)
        self.assertEqual(history[0]["user_id"], user_id)
        self.assertEqual(history[0]["sport"], "Football")

    def test_save_conversion(self):
        user_id = 99887766
        conv_id = DatabaseService.save_conversion(
            user_id=user_id,
            source_code="B9JA123",
            source_bookmaker="Bet9ja",
            sportybet_code="SBCONV1",
            provider_used="Fallback Generator",
        )
        self.assertGreater(conv_id, 0)


if __name__ == "__main__":
    unittest.main()
