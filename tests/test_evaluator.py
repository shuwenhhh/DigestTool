import unittest

from digest_engine.evaluator import evaluate_digest


class EvaluatorTests(unittest.TestCase):
    def test_valid_and_invalid_citations(self) -> None:
        sources = [{"id": "M001", "text": "PCB failed validation."}]
        digest = "# Digest\n- PCB failed validation. [M001]\n- Invented update. [M001]"
        self.assertEqual(
            evaluate_digest(digest, sources),
            {
                "valid_citations": 1,
                "total_bullets": 2,
                "traceable_links": 0,
                "linkable_sources": 0,
                "faithfulness": 0.5,
            },
        )

    def test_link_must_point_to_the_same_source_message(self) -> None:
        url = "https://app.slack.com/archives/C123/p1760000000000100"
        sources = [{"id": "M001", "text": "PCB failed validation.", "source_url": url}]
        valid = f"- PCB failed validation. [M001]({url})"
        invalid = "- PCB failed validation. [M001](https://app.slack.com/archives/C123/p9999999999999999)"
        result = evaluate_digest(f"{valid}\n{invalid}", sources)
        self.assertEqual(result["valid_citations"], 1)
        self.assertEqual(result["traceable_links"], 1)
        self.assertEqual(result["faithfulness"], 0.5)

    def test_rank_label_does_not_break_source_verification(self) -> None:
        sources = [{"id": "M013", "text": "Firmware freeze moved."}]
        result = evaluate_digest("- #3 · Firmware freeze moved. [M013]", sources)
        self.assertEqual(result["valid_citations"], 1)


if __name__ == "__main__":
    unittest.main()
