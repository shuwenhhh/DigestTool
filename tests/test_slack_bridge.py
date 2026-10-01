import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from digest_engine.evaluator import evaluate_digest
from digest_engine.personalization import apply_feedback, load_preferences, migrate_feedback_profile
from slack.bridge import build_digest


ROOT = Path(__file__).resolve().parents[1]


class BridgeTests(unittest.TestCase):
    def test_sensor_noise_downvote_changes_next_digest_only_for_clicker(self) -> None:
        messages = json.loads((ROOT / "data" / "mock_messages.json").read_text(encoding="utf-8"))

        class FakeClient:
            stale = False

            def fetch_messages(self, _channel, simulate_failure=False):
                return messages

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"

            def save_for_test(role, message, direction):
                return apply_feedback(role, message, direction, path=path)

            with (
                patch("slack.bridge.RealSlackClient", return_value=FakeClient()),
                patch("slack.bridge.load_preferences", side_effect=lambda: load_preferences(path)),
                patch("slack.bridge.apply_feedback", side_effect=save_for_test),
                patch("slack.bridge.migrate_feedback_profile", side_effect=lambda role, tagged: migrate_feedback_profile(role, tagged, path=path)),
            ):
                before = build_digest("C123", "electrical_engineer", "dvt", "U1")
                rated = build_digest("C123", "electrical_engineer", "dvt", "U1", "M007", "down")
                next_digest = build_digest("C123", "electrical_engineer", "dvt", "U1")
                other = build_digest("C123", "electrical_engineer", "dvt", "U2")
                undone = build_digest("C123", "electrical_engineer", "dvt", "U1", "M007", "down")
                after_undo = build_digest("C123", "electrical_engineer", "dvt", "U1")

        self.assertIn("M007", [item["id"] for item in before["top"]])
        self.assertNotIn("M007", [item["id"] for item in next_digest["top"]])
        self.assertIn("M007 moved from", rated["feedback_notice"])
        self.assertIn("sensor-noise", next_digest["adjustment"])
        self.assertIn("outside the Top 5", next_digest["adjustment"])
        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", rated["feedback_notice"] + next_digest["adjustment"] + undone["feedback_notice"]))
        self.assertEqual(other["top"], before["top"])
        self.assertNotIn("M007", undone["votes"])
        self.assertEqual(after_undo["top"], before["top"])

    def test_live_digest_citations_resolve_to_ranked_sources(self) -> None:
        messages = json.loads((ROOT / "data" / "mock_messages.json").read_text(encoding="utf-8"))
        for index, message in enumerate(messages, 1):
            message["source_url"] = f"https://app.slack.com/archives/C123/p1760000000{index:06d}"

        class FakeClient:
            stale = False

            def fetch_messages(self, _channel, simulate_failure=False):
                return messages

        with (
            patch("slack.bridge.RealSlackClient", return_value=FakeClient()),
            patch("slack.bridge.migrate_feedback_profile", return_value=False),
        ):
            result = build_digest("C123", "electrical_engineer", "dvt", "U1")

        evaluation = evaluate_digest(result["digest"], messages)
        self.assertEqual(evaluation["valid_citations"], 5)
        self.assertEqual(evaluation["traceable_links"], 5)
        self.assertEqual(evaluation["faithfulness"], 1.0)

    def test_cached_history_is_visibly_marked_stale(self) -> None:
        messages = json.loads((ROOT / "data" / "mock_messages.json").read_text(encoding="utf-8"))

        class StaleClient:
            stale = True

            def fetch_messages(self, _channel, simulate_failure=False):
                return messages

        with (
            patch("slack.bridge.RealSlackClient", return_value=StaleClient()),
            patch("slack.bridge.migrate_feedback_profile", return_value=False),
        ):
            result = build_digest("C123", "pm", "pvt", "U1")

        self.assertTrue(result["stale"])
        self.assertTrue(result["digest"].startswith("⚠️ STALE DATA"))

    def test_feedback_changes_clicking_users_digest_only(self) -> None:
        messages = json.loads((ROOT / "data" / "mock_messages.json").read_text(encoding="utf-8"))

        class FakeClient:
            stale = False

            def fetch_messages(self, _channel, simulate_failure=False):
                return messages

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"

            def save_for_test(role, message, direction):
                return apply_feedback(role, message, direction, path=path)

            with (
                patch("slack.bridge.RealSlackClient", return_value=FakeClient()),
                patch("slack.bridge.load_preferences", side_effect=lambda: load_preferences(path)),
                patch("slack.bridge.apply_feedback", side_effect=save_for_test),
                patch("slack.bridge.migrate_feedback_profile", side_effect=lambda role, tagged: migrate_feedback_profile(role, tagged, path=path)),
            ):
                first = build_digest("C123", "electrical_engineer", "dvt", "U1")
                changed = build_digest("C123", "electrical_engineer", "dvt", "U1", "M011", "up")
                next_digest = build_digest("C123", "electrical_engineer", "dvt", "U1")
                other = build_digest("C123", "electrical_engineer", "dvt", "U2")

        self.assertEqual(changed["movement"], {"id": "M011", "direction": "up", "before": 4, "after": 2})
        self.assertEqual(changed["feedback_notice"], "M011 moved from #4 to #2.")
        self.assertIn("M011 now ranks #2.", next_digest["adjustment"])
        self.assertEqual(first["top"], other["top"])
        self.assertNotEqual(first["top"], changed["top"])
        self.assertEqual(changed["votes"]["M011"], "up")
        self.assertEqual(len(changed["top"]), 5)

    def test_m003_not_relevant_moves_down_and_selected_button_rolls_back(self) -> None:
        """PM + EVT makes M003 visible, so the downvote/undo loop is demoable."""
        messages = json.loads((ROOT / "data" / "mock_messages.json").read_text(encoding="utf-8"))

        class FakeClient:
            stale = False

            def fetch_messages(self, _channel, simulate_failure=False):
                return messages

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"

            def save_for_test(role, message, direction):
                return apply_feedback(role, message, direction, path=path)

            with (
                patch("slack.bridge.RealSlackClient", return_value=FakeClient()),
                patch("slack.bridge.load_preferences", side_effect=lambda: load_preferences(path)),
                patch("slack.bridge.apply_feedback", side_effect=save_for_test),
                patch("slack.bridge.migrate_feedback_profile", side_effect=lambda role, tagged: migrate_feedback_profile(role, tagged, path=path)),
            ):
                before = build_digest("C123", "pm", "evt", "U1")
                rated = build_digest("C123", "pm", "evt", "U1", "M003", "down")
                next_digest = build_digest("C123", "pm", "evt", "U1")
                undone = build_digest("C123", "pm", "evt", "U1", "M003", "down")
                after_undo = build_digest("C123", "pm", "evt", "U1")

        self.assertEqual(before["top"][4]["id"], "M003")
        self.assertEqual(rated["movement"], {"id": "M003", "direction": "down", "before": 5, "after": 7})
        self.assertEqual(rated["feedback_notice"], "M003 moved from #5 to #7.")
        self.assertNotIn("M003", [item["id"] for item in next_digest["top"]])
        self.assertIn("M003 now ranks #7 (outside the Top 5).", next_digest["adjustment"])
        self.assertEqual(undone["feedback_notice"], "Feedback for M003 was undone.")
        self.assertNotIn("M003", undone["votes"])
        self.assertEqual(after_undo["top"], before["top"])


if __name__ == "__main__":
    unittest.main()
