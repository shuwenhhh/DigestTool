"""Check that every digest bullet cites a real, matching source message."""

from __future__ import annotations

import re


CITATION = re.compile(r"\[([MS]\d+)\](?:\((https://[^\s)]+)\))?$")
RANK_PREFIX = re.compile(r"^#\d+ · ")


def evaluate_digest(digest: str, source_messages: list[dict]) -> dict:
    sources = {message["id"]: message for message in source_messages}
    bullets = [line[2:] for line in digest.splitlines() if line.startswith("- ")]
    valid = 0
    linked = 0
    for bullet in bullets:
        match = CITATION.search(bullet)
        if not match:
            continue
        source = sources.get(match.group(1))
        cited_text = RANK_PREFIX.sub("", bullet[:match.start()].strip())
        if source is None or source["text"] != cited_text:
            continue
        expected_url = source.get("source_url")
        if expected_url and match.group(2) != expected_url:
            continue
        if not expected_url and match.group(2):
            continue
        valid += 1
        if expected_url:
            linked += 1
    total = len(bullets)
    return {
        "valid_citations": valid,
        "total_bullets": total,
        "traceable_links": linked,
        "linkable_sources": sum(bool(message.get("source_url")) for message in source_messages),
        "faithfulness": valid / total if total else 0.0,
    }
