import unittest
from builder import CustomSlipBuilder


class TestCustomSlipBuilder(unittest.TestCase):
    def test_custom_slip_generation_95_prob(self):
        res = CustomSlipBuilder.generate_custom_slip(
            target_odds=2.0, game_count=3, min_probability=95.0
        )
        self.assertEqual(res.min_probability, 95.0)
        self.assertIn("CUSTOM MULTI-SPORT PREDICTION SLIP", res.formatted_summary)

    def test_custom_slip_generation_85_prob(self):
        res = CustomSlipBuilder.generate_custom_slip(
            target_odds=5.0, game_count=4, min_probability=60.0
        )
        self.assertEqual(res.min_probability, 60.0)
        self.assertIsNotNone(res.formatted_summary)


if __name__ == "__main__":
    unittest.main()
