import unittest

from digest.evaluator import evaluate_digest


class EvaluatorTests(unittest.TestCase):
    def test_valid_and_invalid_citations(self) -> None:
        sources = [{"id": "M001", "text": "PCB failed validation."}]
        digest = "# Digest\n- PCB failed validation. [M001]\n- Invented update. [M001]"
        self.assertEqual(
            evaluate_digest(digest, sources),
            {"valid_citations": 1, "total_bullets": 2, "faithfulness": 0.5},
        )


if __name__ == "__main__":
    unittest.main()
