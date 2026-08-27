import unittest
from channel_monitor import ChannelMonitorService
from code_editor import CodeEditorEngine
from learning_engine import StrategyLearningEngine


class TestChannelAndEditor(unittest.TestCase):
    def test_code_editor_filtering(self):
        res = CodeEditorEngine.analyze_and_edit_code("BC9910C", channel_source="t.me/jhgfdghgdhjjj")
        self.assertEqual(res.original_code, "BC9910C")
        self.assertGreater(res.original_legs_count, res.kept_legs_count)
        self.assertIn("EDITED & FILTERED", res.formatted_summary)
        self.assertIn("*Removed High-Risk Legs:*", res.formatted_summary)

    def test_channel_monitor_report(self):
        report = ChannelMonitorService.format_channels_report()
        self.assertIn("TELEGRAM CHANNEL LISTENER", report)
        self.assertIn("jhgfdghgdhjjj", report)
        self.assertIn("thirty9bilns", report)
        self.assertIn("+uvIZ9oqbUGZlZjM8", report)

    def test_learning_engine_report(self):
        report = StrategyLearningEngine.format_learning_report()
        self.assertIn("BETTING STRATEGY & COMBINATION LEARNING ENGINE", report)
        self.assertIn("Double Chance + Over 1.5 Goals", report)


if __name__ == "__main__":
    unittest.main()
