import unittest
from builder import CustomSlipBuilder


class TestCustomSlipBuilder(unittest.TestCase):
    def test_custom_slip_generation_95_prob(self):
        res = CustomSlipBuilder.generate_custom_slip(
            target_odds=2.0, game_count=3, min_probability=95.0
        )
        self.assertIsNotNone(res.booking_code)
        self.assertEqual(res.min_probability, 95.0)
        self.assertIn("CUSTOM MULTI-SPORT PREDICTION SLIP", res.formatted_summary)
        self.assertIn("*Minimum Probability:* *95%*", res.formatted_summary)

    def test_custom_slip_generation_85_prob(self):
        res = CustomSlipBuilder.generate_custom_slip(
            target_odds=5.0, game_count=4, min_probability=85.0
        )
        self.assertEqual(res.min_probability, 85.0)
        self.assertGreater(res.actual_odds, 1.0)


if __name__ == "__main__":
    unittest.main()
