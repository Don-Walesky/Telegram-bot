import unittest
from calculator import BetCalculator
from fixtures import PredictionsService
from sportybet import SportyBetService


class TestSportyBetModules(unittest.TestCase):
    def test_booking_url_generation(self):
        url = SportyBetService.get_booking_url("BC12345", country_code="ng")
        self.assertEqual(url, "https://www.sportybet.com/ng/?shareCode=BC12345")

    def test_parse_booking_code(self):
        parsed = SportyBetService.parse_booking_code("Hey, check out this code BC9910A on SportyBet")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.booking_code, "BC9910A")
        self.assertIn("shareCode=BC9910A", parsed.share_url)

    def test_generate_booking_code(self):
        code = SportyBetService.generate_booking_code(prefix="CST")
        self.assertTrue(code.startswith("CST"))
        self.assertEqual(len(code), 8)

    def test_accumulator_calculator(self):
        odds = [1.50, 2.00, 1.80]
        res = BetCalculator.calculate_accumulator(odds, stake=1000)
        self.assertEqual(res["total_odds"], 5.4)
        self.assertEqual(res["gross_payout"], 5400.0)
        self.assertEqual(res["bonus_pct"], 3.0)

    def test_daily_predictions_format(self):
        tips_msg = PredictionsService.format_daily_tips_message()
        self.assertIn("HIGH-PROBABILITY MULTI-SPORT PREDICTIONS", tips_msg)
        self.assertTrue("Accumulator Total Odds:" in tips_msg or "No unstarted matches met" in tips_msg)


if __name__ == "__main__":
    unittest.main()
