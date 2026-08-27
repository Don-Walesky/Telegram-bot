import unittest
from channel_siever import ChannelSlipSiever
from database import DatabaseService


class TestChannelSlipSiever(unittest.TestCase):
    def setUp(self):
        DatabaseService.init_db()

    def test_scan_and_sieve_channel_slips(self):
        res = ChannelSlipSiever.scan_and_sieve_channel_slips(min_probability=85.0, game_count=5)
        self.assertIsNotNone(res)
        self.assertEqual(len(res.picks), 5)
        self.assertTrue(res.success)

    def test_scan_and_sieve_high_probability(self):
        res = ChannelSlipSiever.scan_and_sieve_channel_slips(min_probability=95.0, game_count=3)
        self.assertIsNotNone(res)
        self.assertEqual(len(res.picks), 3)


if __name__ == "__main__":
    unittest.main()
