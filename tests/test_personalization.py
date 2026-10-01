import json
import tempfile
import unittest
from pathlib import Path

from digest.config_loader import load_phase_weights, load_role_weights
from digest.personalization import apply_feedback, feedback_state, load_preferences, role_preferences
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

    def test_vote_can_be_undone_and_switched(self) -> None:
        message = {"id": "M006", "tags": ["SUPPLY_CHAIN"], "topic": "supply-chain"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            apply_feedback("supply_chain", message, "down", path=path)
            preferences, boosts = role_preferences(load_preferences(path), "supply_chain")
            votes, topics, _ = feedback_state(load_preferences(path), "supply_chain")
            self.assertEqual((preferences["SUPPLY_CHAIN"], boosts["M006"], topics["supply-chain"]), (0.85, -0.15, -0.35))
            self.assertEqual(votes["M006"], "down")

            apply_feedback("supply_chain", message, "down", path=path)
            preferences, boosts = role_preferences(
                load_preferences(path), "supply_chain"
            )
            votes, topics, _ = feedback_state(load_preferences(path), "supply_chain")
            self.assertEqual(preferences["SUPPLY_CHAIN"], 1.0)
            self.assertNotIn("M006", boosts)
            self.assertNotIn("supply-chain", topics)
            self.assertNotIn("M006", votes)

            apply_feedback("supply_chain", message, "up", path=path)
            apply_feedback("supply_chain", message, "down", path=path)
            votes, topics, _ = feedback_state(load_preferences(path), "supply_chain")
            self.assertEqual(votes["M006"], "down")
            self.assertEqual(topics["supply-chain"], -0.35)

    def test_undo_after_weight_saturation_restores_correct_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            messages = [
                {"id": f"M{i:03d}", "tags": ["TEST_RESULT"], "topic": "sensor-noise"}
                for i in range(1, 6)
            ]
            for message in messages:
                apply_feedback("U1:electrical_engineer", message, "up", path=path)
            apply_feedback("U1:electrical_engineer", messages[0], "up", path=path)
            preferences, _ = role_preferences(load_preferences(path), "U1:electrical_engineer")
            self.assertEqual(preferences["TEST_RESULT"], 1.6)
            apply_feedback("U1:electrical_engineer", messages[1], "up", path=path)
            preferences, _ = role_preferences(load_preferences(path), "U1:electrical_engineer")
            self.assertEqual(preferences["TEST_RESULT"], 1.45)


if __name__ == "__main__":
    unittest.main()
