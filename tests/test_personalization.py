import json
import tempfile
import unittest
from pathlib import Path

from digest.config_loader import load_phase_weights, load_role_weights
from digest.personalization import apply_feedback, load_preferences, role_preferences
from digest.ranker import rank_messages
from digest.tagger import tag_messages


ROOT = Path(__file__).resolve().parents[1]


class PersonalizationTests(unittest.TestCase):
    def test_up_feedback_persists_and_moves_m011(self) -> None:
        with (ROOT / "data" / "mock_messages.json").open(encoding="utf-8") as handle:
            messages = tag_messages(json.load(handle))
        target = next(message for message in messages if message["id"] == "M011")
        _, role_weights = load_role_weights("electrical_engineer")
        _, phase_weights = load_phase_weights("dvt")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            path.write_text(
                '{"electrical_engineer":{"TEST_RESULT":1.0,"_message_boosts":{}}}',
                encoding="utf-8",
            )
            before_prefs, before_boosts = role_preferences(
                load_preferences(path), "electrical_engineer"
            )
            before = rank_messages(
                messages, role_weights, phase_weights, before_prefs, before_boosts
            )
            before_rank = [item["id"] for item in before].index("M011") + 1

            changes = apply_feedback(
                "electrical_engineer", target, "up", path=path
            )
            after_prefs, after_boosts = role_preferences(
                load_preferences(path), "electrical_engineer"
            )
            after = rank_messages(
                messages, role_weights, phase_weights, after_prefs, after_boosts
            )
            after_rank = [item["id"] for item in after].index("M011") + 1

            self.assertIn(("TEST_RESULT", 1.0, 1.15), changes)
            self.assertEqual(after_prefs["TEST_RESULT"], 1.15)
            self.assertEqual(after_boosts["M011"], 0.15)
            self.assertEqual(before_rank, 4)
            self.assertEqual(after_rank, 2)

    def test_down_feedback_is_bounded(self) -> None:
        message = {"id": "M006", "tags": ["SUPPLY_CHAIN"]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            for _ in range(10):
                apply_feedback("supply_chain", message, "down", path=path)
            preferences, boosts = role_preferences(
                load_preferences(path), "supply_chain"
            )
            self.assertEqual(preferences["SUPPLY_CHAIN"], 0.4)
            self.assertEqual(boosts["M006"], -0.45)


if __name__ == "__main__":
    unittest.main()
