import unittest

from digest.tagger import TAGS, tag_message


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


if __name__ == "__main__":
    unittest.main()
