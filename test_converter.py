import unittest
from unittest.mock import patch, MagicMock
from code_converter import BetCodeConverterService, ConversionResult
from sportybet import SportyBetService


class TestBetCodeConverter(unittest.TestCase):
    def test_fallback_conversion(self):
        res = BetCodeConverterService.convert_code_to_sportybet("B9JA9999", "bet9ja")
        self.assertTrue(res.success)
        self.assertEqual(res.source_code, "B9JA9999")
        self.assertIn("sportybet", res.share_url)
        self.assertIn("SB9999", res.sportybet_code)

    def test_format_conversion_report(self):
        res = ConversionResult(
            success=True,
            source_code="B9JA1234",
            source_bookmaker="Bet9ja",
            destination_bookmaker="SportyBet",
            sportybet_code="SB1234",
            share_url="https://www.sportybet.com/ng/?shareCode=SB1234",
            matches_count=4,
            message="Successfully converted",
            provider_used="RapidAPI ConvertBetCodes",
        )
        report = BetCodeConverterService.format_conversion_report(res)
        self.assertIn("BET CODE CONVERSION TO SPORTYBET", report)
        self.assertIn("B9JA1234", report)
        self.assertIn("SB1234", report)
        self.assertIn("RapidAPI ConvertBetCodes", report)

    def test_sportybet_service_conversion_method(self):
        res = SportyBetService.convert_external_code("1X223344", "1xbet")
        self.assertTrue(res.success)
        self.assertEqual(res.source_code, "1X223344")
        self.assertIn("SportyBet", res.destination_bookmaker)

    @patch("code_converter.httpx.Client")
    def test_rapidapi_mock_conversion(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "converted_code": "SPORTY777",
            "matches_count": 5,
        }
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch.object(BetCodeConverterService, "get_rapidapi_key", return_value="dummy_key"):
            res = BetCodeConverterService.convert_code_to_sportybet("BET9JA88", "bet9ja")
            self.assertTrue(res.success)
            self.assertEqual(res.sportybet_code, "SPORTY777")
            self.assertEqual(res.provider_used, "RapidAPI ConvertBetCodes")


if __name__ == "__main__":
    unittest.main()
