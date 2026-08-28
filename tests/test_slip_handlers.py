import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.slip_handlers import custom_command, handle_slip_callback
from builder import CustomSlipResult
from sportybet_booking import BookingSlipResponse


class TestSlipHandlers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.update = MagicMock()
        self.update.message = AsyncMock()
        self.context = MagicMock()
        self.context.user_data = {}

        self.mock_custom_res = CustomSlipResult(
            target_odds=3.0,
            actual_odds=3.25,
            game_count=5,
            min_probability=85.0,
            selections=[],
            booking_code="BUILDBC123",
            formatted_summary="🎯 Custom Slip Summary",
        )

    async def test_custom_command(self):
        self.context.user_data["wiz"] = {"stale_date": "Yesterday"}
        await custom_command(self.update, self.context)
        self.assertEqual(self.context.user_data["wiz"], {})
        self.update.message.reply_text.assert_called_once()
        self.assertIn("Custom Slip Builder Wizard", self.update.message.reply_text.call_args[0][0])

    async def test_handle_slip_callback_wiz_start(self):
        query = MagicMock()
        query.message = AsyncMock()
        handled = await handle_slip_callback(query, "wiz_start", self.context)
        self.assertTrue(handled)
        query.message.edit_text.assert_called_once()
        self.assertIn("Custom Slip Builder Wizard", query.message.edit_text.call_args[0][0])

    async def test_handle_slip_callback_wiz_date(self):
        query = MagicMock()
        query.message = AsyncMock()
        handled = await handle_slip_callback(query, "wiz_date_Tomorrow", self.context)
        self.assertTrue(handled)
        self.assertEqual(self.context.user_data["wiz"]["date"], "Tomorrow")
        self.assertIn("Step 2 of 5", query.message.edit_text.call_args[0][0])

    async def test_handle_slip_callback_wiz_sport(self):
        query = MagicMock()
        query.message = AsyncMock()
        self.context.user_data["wiz"] = {"date": "Tomorrow"}
        handled = await handle_slip_callback(query, "wiz_sport_Football", self.context)
        self.assertTrue(handled)
        self.assertEqual(self.context.user_data["wiz"]["sport"], "Football")
        self.assertIn("Step 3 of 5", query.message.edit_text.call_args[0][0])

    async def test_handle_slip_callback_wiz_odds(self):
        query = MagicMock()
        query.message = AsyncMock()
        self.context.user_data["wiz"] = {"date": "Tomorrow", "sport": "Football"}
        handled = await handle_slip_callback(query, "wiz_odds_3.0", self.context)
        self.assertTrue(handled)
        self.assertEqual(self.context.user_data["wiz"]["odds"], 3.0)
        self.assertIn("Step 4 of 5", query.message.edit_text.call_args[0][0])

    async def test_handle_slip_callback_wiz_count(self):
        query = MagicMock()
        query.message = AsyncMock()
        self.context.user_data["wiz"] = {"date": "Tomorrow", "sport": "Football", "odds": 3.0}
        handled = await handle_slip_callback(query, "wiz_count_5", self.context)
        self.assertTrue(handled)
        self.assertEqual(self.context.user_data["wiz"]["count"], 5)
        self.assertIn("Step 5 of 5", query.message.edit_text.call_args[0][0])

    @patch("handlers.slip_handlers.DatabaseService.save_slip")
    @patch("handlers.slip_handlers.CustomSlipBuilder.generate_custom_slip")
    async def test_handle_slip_callback_wiz_prob(self, mock_generate, mock_save_slip):
        mock_generate.return_value = self.mock_custom_res
        query = MagicMock()
        query.message = AsyncMock()
        query.from_user.id = 123456
        self.context.user_data["wiz"] = {"date": "Tomorrow", "sport": "Football", "odds": 3.0, "count": 5}

        handled = await handle_slip_callback(query, "wiz_prob_85", self.context)
        self.assertTrue(handled)
        mock_generate.assert_called_once_with(3.0, 5, 85.0, "Tomorrow", "Football")
        mock_save_slip.assert_called_once()
        self.assertEqual(self.context.user_data["current_slip"], self.mock_custom_res)

    async def test_handle_slip_callback_unhandled(self):
        query = MagicMock()
        query.message = AsyncMock()
        handled = await handle_slip_callback(query, "chan_wiz_start", self.context)
        self.assertFalse(handled)

    def test_user_state_isolation(self):
        context_user1 = MagicMock()
        context_user1.user_data = {}
        context_user2 = MagicMock()
        context_user2.user_data = {}

        context_user1.user_data.setdefault("wiz", {})["date"] = "Today"
        context_user2.user_data.setdefault("wiz", {})["date"] = "Tomorrow"

        self.assertEqual(context_user1.user_data["wiz"]["date"], "Today")
        self.assertEqual(context_user2.user_data["wiz"]["date"], "Tomorrow")


if __name__ == "__main__":
    unittest.main()
