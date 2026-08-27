import unittest
from http_client import HTTPClientProvider


class TestHTTPClientProvider(unittest.TestCase):
    def tearDown(self):
        HTTPClientProvider.close_all()

    def test_client_reuse(self):
        client1 = HTTPClientProvider.get_client(timeout=8.0)
        client2 = HTTPClientProvider.get_client(timeout=8.0)
        self.assertIs(client1, client2)
        self.assertFalse(client1.is_closed)

    def test_client_different_timeouts(self):
        client_8 = HTTPClientProvider.get_client(timeout=8.0)
        client_10 = HTTPClientProvider.get_client(timeout=10.0)
        self.assertIsNot(client_8, client_10)

    def test_client_close_all(self):
        client1 = HTTPClientProvider.get_client(timeout=8.0)
        client2 = HTTPClientProvider.get_client(timeout=10.0)
        HTTPClientProvider.close_all()
        self.assertTrue(client1.is_closed)
        self.assertTrue(client2.is_closed)


if __name__ == "__main__":
    unittest.main()
