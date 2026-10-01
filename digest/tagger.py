"""Deterministic message tagging for the demo corpus."""

from __future__ import annotations

from collections.abc import Iterable


TAGS = [
    "BOM_CHANGE",
    "ECO",
    "BLOCKER",
    "SCHEDULE",
    "TEST_RESULT",
    "DECISION",
    "SUPPLY_CHAIN",
    "QUALITY",
    "DESIGN_CHANGE",
]

# More specific rules come first only for readability; output follows TAGS order.
TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "BOM_CHANGE": ("bom", "cost increased", "alternate encoder"),
    "ECO": ("eco-",),
    "BLOCKER": ("blocked", "blocking", "blockers", "unresolved", "only after"),
    "SCHEDULE": ("scheduled", "by october", "due ", "moved to"),
    "TEST_RESULT": ("failed", "passed", "validation at", "threshold", "sign-off"),
    "DECISION": ("approved", "decided", "will proceed"),
    "SUPPLY_CHAIN": ("supplier", "vendor", "lead time", "can ship", "harness arrives"),
    "QUALITY": ("inspection", "scratches", "corrective action", "cracked"),
    "DESIGN_CHANGE": ("changed", "change", "layout update", "cad release", "adds a"),
}

URGENCY_SIGNALS: tuple[tuple[str, float], ...] = (
    ("blocking", 0.37),
    ("blocked", 0.37),
    ("failed", 0.55),
    ("unresolved", 0.35),
    ("only after", 0.35),
    ("increased lead time", 0.42),
    ("due friday", 0.30),
    ("tomorrow", 0.25),
    ("delay", 0.35),
    ("exceeded", 0.42),
)


def _urgency(text: str) -> float:
    lower = text.lower()
    score = 0.0
    for phrase, weight in URGENCY_SIGNALS:
        if phrase in lower:
            score += weight
    if score == 0.0:
        score = 0.18
    return round(min(score, 1.0), 2)


def tag_message(message: dict) -> dict:
    """Return a copy of a Slack message enriched with tags and urgency."""
    lower = message["text"].lower()
    tags = [
        tag
        for tag in TAGS
        if any(keyword in lower for keyword in TAG_KEYWORDS[tag])
    ]
    specific_topics = (
        ("sensor noise", "sensor-noise"),
        ("exit review", "dvt-exit-review"),
        ("firmware freeze", "firmware-freeze"),
        ("can bus", "can-bus"),
        ("thermal", "thermal-validation"),
        ("drop test", "drop-test"),
    )
    topic = next(
        (name for keyword, name in specific_topics if keyword in lower),
        tags[0].lower().replace("_", "-") if tags else "general",
    )
    return {**message, "tags": tags, "topic": topic, "urgency": _urgency(message["text"])}


def tag_messages(messages: Iterable[dict]) -> list[dict]:
    return [tag_message(message) for message in messages]
