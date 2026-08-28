import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.scan_handlers import (
    today_command,
    tomorrow_command,
    sports_command,
    scan_command,
    handle_scan_callback,
)
from sportybet_booking import BookingSlipResponse


class TestScanHandlers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.update = MagicMock()
        self.update.message = AsyncMock()
        self.context = MagicMock()
        self.context.user_data = {}

        self.mock_slip = BookingSlipResponse(
            success=True,
            booking_code="TESTBC99",
            share_url="https://www.sportybet.com/ng/?shareCode=TESTBC99",
            picks=[],
            total_odds=2.5,
            formatted_summary="🎯 Test Slip Summary",
        )

    @patch("handlers.scan_handlers.BettingService.execute_scan_pipeline")
    async def test_today_command(self, mock_execute):
        mock_execute.return_value = self.mock_slip
        await today_command(self.update, self.context)
        self.assertEqual(self.context.user_data["target_date"], "Today")
        self.assertEqual(self.context.user_data["current_slip"], self.mock_slip)
        self.assertEqual(self.update.message.reply_text.call_count, 2)
        mock_execute.assert_called_once_with("Today", "All")

    @patch("handlers.scan_handlers.BettingService.execute_scan_pipeline")
    async def test_tomorrow_command(self, mock_execute):
        mock_execute.return_value = self.mock_slip
        await tomorrow_command(self.update, self.context)
        self.assertEqual(self.context.user_data["target_date"], "Tomorrow")
        self.assertEqual(self.context.user_data["current_slip"], self.mock_slip)
        mock_execute.assert_called_once_with("Tomorrow", "All")

    async def test_sports_command(self):
        await sports_command(self.update, self.context)
        self.update.message.reply_text.assert_called_once()
        self.assertIn("target sport category", self.update.message.reply_text.call_args[0][0])

    @patch("handlers.scan_handlers.BettingService.execute_scan_pipeline")
    async def test_handle_scan_callback_today(self, mock_execute):
        mock_execute.return_value = self.mock_slip
        query = MagicMock()
        query.message = AsyncMock()

        handled = await handle_scan_callback(query, "cmd_today", self.context)
        self.assertTrue(handled)
        self.assertEqual(self.context.user_data["target_date"], "Today")
        mock_execute.assert_called_once_with("Today", "All")

    async def test_handle_scan_callback_unhandled(self):
        query = MagicMock()
        query.message = AsyncMock()
        handled = await handle_scan_callback(query, "cmd_unrelated", self.context)
        self.assertFalse(handled)


if __name__ == "__main__":
    unittest.main()
