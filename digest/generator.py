"""Faithful, citation-first Markdown digest generation."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable


SECTION_BY_TAG = {
    "BLOCKER": "🚨 Critical",
    "TEST_RESULT": "🧪 Test Results",
    "QUALITY": "✅ Quality",
    "SUPPLY_CHAIN": "📦 Supply Chain",
    "SCHEDULE": "📅 Schedule",
    "BOM_CHANGE": "🧾 BOM Changes",
    "ECO": "🛠 ECOs",
    "DESIGN_CHANGE": "📐 Design Changes",
    "DECISION": "💡 Decisions",
    "UNTAGGED": "📌 Other Updates",
}

SECTION_PRIORITY = [
    "BLOCKER",
    "SCHEDULE",
    "TEST_RESULT",
    "QUALITY",
    "SUPPLY_CHAIN",
    "BOM_CHANGE",
    "ECO",
    "DESIGN_CHANGE",
    "DECISION",
]


def _section_for(message: dict) -> str:
    tags = message.get("tags", [])
    section_tag = next((tag for tag in SECTION_PRIORITY if tag in tags), None)
    if section_tag is None:
        section_tag = message.get("score_tag", "UNTAGGED")
    return SECTION_BY_TAG.get(section_tag, "📌 Other Updates")


def generate_digest(
    top_messages: Iterable[dict], role_name: str, phase_name: str
) -> str:
    """Render supplied message text with an ID linked to its source when available."""
    messages = list(top_messages)
    if len(messages) > 5:
        raise ValueError("Digest generator accepts at most five ranked messages")

    sections: OrderedDict[str, list[dict]] = OrderedDict()
    for message in messages:
        section = _section_for(message)
        sections.setdefault(section, []).append(message)

    lines = ["# 🌅 EverCurrent Daily Digest", f"{role_name} · {phase_name}"]
    for section, items in sections.items():
        lines.extend(["", f"## {section}"])
        for message in items:
            # Verbatim source text is intentional: templates cannot invent facts.
            citation = f"[{message['id']}]"
            if message.get("source_url"):
                citation += f"({message['source_url']})"
            lines.append(f"- {message['text']} {citation}")
    return "\n".join(lines)
