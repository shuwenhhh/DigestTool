import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from digest.personalization import apply_feedback, load_preferences
from slack.bridge import build_digest


ROOT = Path(__file__).resolve().parents[1]


class BridgeTests(unittest.TestCase):
    def test_cached_history_is_visibly_marked_stale(self) -> None:
        messages = json.loads((ROOT / "data" / "mock_messages.json").read_text(encoding="utf-8"))

        class StaleClient:
            stale = True

            def fetch_messages(self, _channel, simulate_failure=False):
                return messages

        with patch("slack.bridge.RealSlackClient", return_value=StaleClient()):
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
            ):
                first = build_digest("C123", "electrical_engineer", "dvt", "U1")
                changed = build_digest("C123", "electrical_engineer", "dvt", "U1", "M011", "up")
                other = build_digest("C123", "electrical_engineer", "dvt", "U2")

        self.assertEqual(changed["movement"], {"id": "M011", "direction": "up", "before": 4, "after": 2})
        self.assertEqual(first["top"], other["top"])
        self.assertNotEqual(first["top"], changed["top"])
        self.assertEqual(len(changed["top"]), 5)


if __name__ == "__main__":
    unittest.main()
