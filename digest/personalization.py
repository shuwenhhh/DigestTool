"""Persistent, bounded learning from explicit digest feedback."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFERENCES_PATH = ROOT / "data" / "runtime" / "preferences.json"
INITIAL_PREFERENCES_PATH = ROOT / "data" / "preferences.json"
TAG_STEP = 0.15
MESSAGE_STEP = 0.15
TOPIC_STEP = 0.35
MIN_TAG_WEIGHT = 0.4
MAX_TAG_WEIGHT = 1.6
MIN_MESSAGE_BOOST = -0.45
MAX_MESSAGE_BOOST = 0.45
MIN_TOPIC_BOOST = -1.05
MAX_TOPIC_BOOST = 1.05


def load_preferences(path: Path = DEFAULT_PREFERENCES_PATH) -> dict:
    if not path.exists():
        if path != DEFAULT_PREFERENCES_PATH:
            return {}
        path = INITIAL_PREFERENCES_PATH
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def role_preferences(data: dict, role: str) -> tuple[dict[str, float], dict[str, float]]:
    profile = data.get(role, {})
    tag_preferences = {
        key: float(value)
        for key, value in profile.items()
        if not key.startswith("_")
    }
    message_boosts = {
        key: float(value)
        for key, value in profile.get("_message_boosts", {}).items()
    }
    return tag_preferences, message_boosts


def feedback_state(data: dict, role: str) -> tuple[dict[str, str], dict[str, float], dict]:
    profile = data.get(role, {})
    return (
        dict(profile.get("_votes", {})),
        {key: float(value) for key, value in profile.get("_topic_boosts", {}).items()},
        dict(profile.get("_last_feedback", {})),
    )


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
    """Toggle or switch a per-user vote; applying the same vote again undoes it."""
    if direction not in {"up", "down"}:
        raise ValueError("Feedback direction must be 'up' or 'down'")
    data = load_preferences(path)
    profile = data.setdefault(role, {})
    votes = profile.setdefault("_votes", {})
    previous = votes.get(message["id"])
    selected = None if previous == direction else direction
    old_sign = {None: 0, "up": 1, "down": -1}[previous]
    new_sign = {None: 0, "up": 1, "down": -1}[selected]
    change = new_sign - old_sign
    if selected:
        votes[message["id"]] = selected
    else:
        votes.pop(message["id"], None)
    changes: list[tuple[str, float, float]] = []
    raw_tags = profile.setdefault("_raw_tag_weights", {})
    for tag in message.get("tags", []):
        old = float(profile.get(tag, 1.0))
        raw = round(float(raw_tags.get(tag, old)) + TAG_STEP * change, 2)
        raw_tags[tag] = raw
        new = round(min(MAX_TAG_WEIGHT, max(MIN_TAG_WEIGHT, raw)), 2)
        profile[tag] = new
        changes.append((tag, old, new))
    boosts = profile.setdefault("_message_boosts", {})
    old_boost = float(boosts.get(message["id"], 0.0))
    raw_boosts = profile.setdefault("_raw_message_boosts", {})
    raw_boost = round(float(raw_boosts.get(message["id"], old_boost)) + MESSAGE_STEP * change, 2)
    raw_boosts[message["id"]] = raw_boost
    new_boost = round(min(MAX_MESSAGE_BOOST, max(MIN_MESSAGE_BOOST, raw_boost)), 2)
    if new_boost:
        boosts[message["id"]] = new_boost
    else:
        boosts.pop(message["id"], None)
    topic = message.get("topic", "general")
    topics = profile.setdefault("_topic_boosts", {})
    old_topic = float(topics.get(topic, 0.0))
    raw_topics = profile.setdefault("_raw_topic_boosts", {})
    raw_topic = round(float(raw_topics.get(topic, old_topic)) + TOPIC_STEP * change, 2)
    raw_topics[topic] = raw_topic
    new_topic = round(min(MAX_TOPIC_BOOST, max(MIN_TOPIC_BOOST, raw_topic)), 2)
    if new_topic:
        topics[topic] = new_topic
    else:
        topics.pop(topic, None)
    profile["_last_feedback"] = {"id": message["id"], "topic": topic, "state": selected or "neutral"}
    _save_preferences(data, path)
    return changes
