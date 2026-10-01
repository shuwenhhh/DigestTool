import re
import unittest

from digest.generator import generate_digest


class GeneratorTests(unittest.TestCase):
    def test_every_bullet_is_verbatim_and_cited(self) -> None:
        messages = [
            {
                "id": "M001",
                "text": "Thermal validation failed.",
                "score_tag": "TEST_RESULT",
            },
            {
                "id": "M002",
                "text": "Lead time increased.",
                "score_tag": "SUPPLY_CHAIN",
            },
        ]
        digest = generate_digest(messages, "Electrical Engineer", "DVT")
        bullets = [line for line in digest.splitlines() if line.startswith("- ")]
        self.assertEqual(len(bullets), 2)
        self.assertTrue(all(re.search(r"\[M\d{3}\]$", line) for line in bullets))
        for rank, message in enumerate(messages, start=1):
            self.assertIn(f"- #{rank} · {message['text']} [{message['id']}]", digest)

    def test_overall_ranks_remain_visible_across_sections(self) -> None:
        messages = [
            {"id": "M001", "text": "First blocker.", "tags": ["BLOCKER"]},
            {"id": "M002", "text": "Second test.", "tags": ["TEST_RESULT"]},
            {"id": "M003", "text": "Third blocker.", "tags": ["BLOCKER"]},
        ]
        digest = generate_digest(messages, "Electrical Engineer", "DVT")
        self.assertIn("- #1 · First blocker. [M001]", digest)
        self.assertIn("- #3 · Third blocker. [M003]", digest)
        self.assertIn("- #2 · Second test. [M002]", digest)

    def test_rejects_more_than_top_five(self) -> None:
        messages = [
            {"id": f"M{i:03d}", "text": "x", "score_tag": "DECISION"}
            for i in range(6)
        ]
        with self.assertRaisesRegex(ValueError, "at most five"):
            generate_digest(messages, "PM", "DVT")

    def test_real_slack_source_has_clickable_citation(self) -> None:
        url = "https://app.slack.com/archives/C123/p1760000000000100"
        digest = generate_digest(
            [{"id": "M001", "text": "Thermal validation failed.", "source_url": url}],
            "Electrical Engineer",
            "DVT",
        )
        self.assertIn(f"- #1 · Thermal validation failed. [M001]({url})", digest)


if __name__ == "__main__":
    unittest.main()
