import json
import unittest
from pathlib import Path

from digest.config_loader import load_phase_weights, load_role_weights
from digest.ranker import rank_messages, score_message
from digest.tagger import tag_messages


ROOT = Path(__file__).resolve().parents[1]


class RankerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with (ROOT / "data" / "mock_messages.json").open(encoding="utf-8") as handle:
            cls.messages = tag_messages(json.load(handle))

    def test_formula_uses_strongest_tag_and_urgency(self) -> None:
        scored = score_message(
            {"id": "X", "tags": ["TEST_RESULT", "SUPPLY_CHAIN"], "urgency": 0.5},
            {"TEST_RESULT": 1.5, "SUPPLY_CHAIN": 0.4},
            {"TEST_RESULT": 1.4, "SUPPLY_CHAIN": 1.0},
            {},
        )
        self.assertEqual(scored["score_tag"], "TEST_RESULT")
        self.assertAlmostEqual(scored["score"], 2.25)

    def test_roles_have_different_top_five(self) -> None:
        _, phase = load_phase_weights("dvt")
        _, ee = load_role_weights("electrical_engineer")
        _, sc = load_role_weights("supply_chain")
        ee_top = [m["id"] for m in rank_messages(self.messages, ee, phase, {})[:5]]
        sc_top = [m["id"] for m in rank_messages(self.messages, sc, phase, {})[:5]]
        self.assertNotEqual(ee_top, sc_top)
        self.assertGreaterEqual(len(set(ee_top) ^ set(sc_top)), 2)

    def test_pm_evt_and_pvt_have_distinct_phase_priorities(self) -> None:
        _, pm = load_role_weights("pm")
        _, evt = load_phase_weights("evt")
        _, pvt = load_phase_weights("pvt")
        evt_top = [m["id"] for m in rank_messages(self.messages, pm, evt, {})[:5]]
        pvt_top = [m["id"] for m in rank_messages(self.messages, pm, pvt, {})[:5]]
        self.assertIn("M007", evt_top)  # DVT-style validation signal is early-stage critical.
        self.assertIn("M011", evt_top)
        self.assertTrue({"M005", "M006", "M012"}.issubset(pvt_top))
        self.assertEqual(set(evt_top) & set(pvt_top), set())


if __name__ == "__main__":
    unittest.main()
