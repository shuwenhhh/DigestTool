"""Check that every digest bullet cites a real, matching source message."""

from __future__ import annotations

import re


CITATION = re.compile(r"\[([MS]\d+)\]$")


def evaluate_digest(digest: str, source_messages: list[dict]) -> dict:
    sources = {message["id"]: message["text"] for message in source_messages}
    bullets = [line[2:] for line in digest.splitlines() if line.startswith("- ")]
    valid = 0
    for bullet in bullets:
        match = CITATION.search(bullet)
        if match and sources.get(match.group(1)) == bullet[:match.start()].strip():
            valid += 1
    total = len(bullets)
    return {
        "valid_citations": valid,
        "total_bullets": total,
        "faithfulness": valid / total if total else 0.0,
    }
