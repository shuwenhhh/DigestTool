"""Persistent, bounded learning from explicit digest feedback."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFERENCES_PATH = ROOT / "data" / "preferences.json"
TAG_STEP = 0.15
MESSAGE_STEP = 0.15
MIN_TAG_WEIGHT = 0.4
MAX_TAG_WEIGHT = 1.6
MIN_MESSAGE_BOOST = -0.45
MAX_MESSAGE_BOOST = 0.45


def load_preferences(path: Path = DEFAULT_PREFERENCES_PATH) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def role_preferences(data: dict, role: str) -> tuple[dict[str, float], dict[str, float]]:
    profile = data.get(role, {})
    tag_preferences = {
        key: float(value)
        for key, value in profile.items()
        if key != "_message_boosts"
    }
    message_boosts = {
        key: float(value)
        for key, value in profile.get("_message_boosts", {}).items()
    }
    return tag_preferences, message_boosts


def _save_preferences(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="preferences-", suffix=".json", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
        raise


def apply_feedback(
    role: str,
    message: dict,
    direction: str,
    path: Path = DEFAULT_PREFERENCES_PATH,
) -> list[tuple[str, float, float]]:
    """Update topic affinity plus a small explicit boost for the rated item."""
    if direction not in {"up", "down"}:
        raise ValueError("Feedback direction must be 'up' or 'down'")
    delta = TAG_STEP if direction == "up" else -TAG_STEP
    message_delta = MESSAGE_STEP if direction == "up" else -MESSAGE_STEP
    data = load_preferences(path)
    profile = data.setdefault(role, {})
    changes: list[tuple[str, float, float]] = []
    for tag in message.get("tags", []):
        old = float(profile.get(tag, 1.0))
        new = round(min(MAX_TAG_WEIGHT, max(MIN_TAG_WEIGHT, old + delta)), 2)
        profile[tag] = new
        changes.append((tag, old, new))
    boosts = profile.setdefault("_message_boosts", {})
    old_boost = float(boosts.get(message["id"], 0.0))
    boosts[message["id"]] = round(
        min(MAX_MESSAGE_BOOST, max(MIN_MESSAGE_BOOST, old_boost + message_delta)),
        2,
    )
    _save_preferences(data, path)
    return changes
