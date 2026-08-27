import os
import unittest
from config import Config, parse_bool, EnvironmentConfig, BettingEngineConfig, ExternalServiceConfig


class TestConfiguration(unittest.TestCase):
    def test_default_config_loading(self):
        cfg = Config()
        self.assertEqual(cfg.betting.min_implied_probability, 60.0)
        self.assertEqual(cfg.betting.max_implied_probability, 95.0)
        self.assertEqual(cfg.betting.default_scan_legs, 5)
        self.assertEqual(cfg.services.livescore_timeout, 8.0)
        self.assertEqual(cfg.services.booking_api_timeout, 10.0)
        self.assertIn("Football", cfg.domain.supported_sports)

    def test_parse_bool_helper(self):
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("1"))
        self.assertTrue(parse_bool("YES"))
        self.assertTrue(parse_bool("on"))
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool(None))
        self.assertFalse(parse_bool(None, default=False))
        self.assertTrue(parse_bool(None, default=True))

    def test_validation_invalid_probability(self):
        with self.assertRaises(ValueError):
            cfg = Config(betting=BettingEngineConfig(min_implied_probability=95.0, max_implied_probability=60.0))
            cfg.validate()

    def test_validation_invalid_timeout(self):
        with self.assertRaises(ValueError):
            cfg = Config(services=ExternalServiceConfig(livescore_timeout=-1.0))
            cfg.validate()

    def test_environment_override(self):
        os.environ["TEST_BOT_SECRET_TOKEN"] = "test_secret_val"
        env_cfg = EnvironmentConfig(telegram_bot_token=os.getenv("TEST_BOT_SECRET_TOKEN"))
        self.assertEqual(env_cfg.telegram_bot_token, "test_secret_val")
        del os.environ["TEST_BOT_SECRET_TOKEN"]


if __name__ == "__main__":
    unittest.main()
