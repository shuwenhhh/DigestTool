import unittest

from digest_engine.tagger import TAGS, tag_message


class TaggerTests(unittest.TestCase):
    def test_all_expected_tags_are_declared(self) -> None:
        self.assertEqual(len(TAGS), 9)

    def test_failed_blocking_message_has_tags_and_high_urgency(self) -> None:
        tagged = tag_message(
            {"id": "M001", "text": "PCB Rev C failed validation, blocking sign-off."}
        )
        self.assertEqual(tagged["tags"], ["BLOCKER", "TEST_RESULT"])
        self.assertEqual(tagged["urgency"], 0.92)

    def test_supply_chain_message(self) -> None:
        tagged = tag_message(
            {"id": "M002", "text": "Supplier lead time increased to 7 weeks."}
        )
        self.assertIn("SUPPLY_CHAIN", tagged["tags"])

    def test_blocker_subtopics_do_not_all_share_one_topic(self) -> None:
        examples = {
            "M001": ("PCB Rev C failed thermal validation at 75°C, blocking electrical sign-off.", "thermal-validation"),
            "M013": ("The firmware freeze moved to October 3 due to unresolved CAN bus issues.", "firmware-freeze"),
            "M014": ("CAN bus debugging is blocked until the new harness arrives tomorrow.", "can-bus"),
            "M018": ("DVT exit review will proceed only after thermal and drop-test blockers close.", "dvt-exit-review"),
        }
        for message_id, (body, topic) in examples.items():
            with self.subTest(message_id=message_id):
                tagged = tag_message({"id": message_id, "text": body})
                self.assertEqual(tagged["topic"], topic)
                self.assertTrue(tagged["topic_is_specific"])

    def test_generic_topic_is_marked_broad(self) -> None:
        tagged = tag_message({"id": "M005", "text": "DVT build is scheduled for October 8."})
        self.assertEqual(tagged["topic"], "schedule")
        self.assertFalse(tagged["topic_is_specific"])


if __name__ == "__main__":
    unittest.main()
