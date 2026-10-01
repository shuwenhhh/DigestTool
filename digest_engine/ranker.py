"""Explainable role × phase × preference ranking."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


DEFAULT_WEIGHT = 1.0


def score_message(
    message: dict,
    role_weights: Mapping[str, float],
    phase_weights: Mapping[str, float],
    preferences: Mapping[str, float],
    message_boosts: Mapping[str, float] | None = None,
    topic_boosts: Mapping[str, float] | None = None,
) -> dict:
    """Score a tagged message using its strongest tag signal."""
    tags = message.get("tags", [])
    tag_scores = {
        tag: role_weights.get(tag, DEFAULT_WEIGHT)
        * phase_weights.get(tag, DEFAULT_WEIGHT)
        * preferences.get(tag, DEFAULT_WEIGHT)
        for tag in tags
    }
    if tag_scores:
        score_tag, relevance = max(tag_scores.items(), key=lambda pair: pair[1])
    else:
        score_tag, relevance = "UNTAGGED", 0.0
    explicit_feedback = (message_boosts or {}).get(message["id"], 0.0)
    topic_feedback = (topic_boosts or {}).get(message.get("topic", "general"), 0.0)
    score = relevance + float(message.get("urgency", 0.0)) * 0.3 + explicit_feedback + topic_feedback
    return {
        **message,
        "score": round(score, 4),
        "score_tag": score_tag,
        "tag_scores": {tag: round(value, 4) for tag, value in tag_scores.items()},
        "feedback_boost": explicit_feedback,
        "topic_boost": topic_feedback,
    }


def rank_messages(
    messages: Iterable[dict],
    role_weights: Mapping[str, float],
    phase_weights: Mapping[str, float],
    preferences: Mapping[str, float],
    message_boosts: Mapping[str, float] | None = None,
    topic_boosts: Mapping[str, float] | None = None,
) -> list[dict]:
    scored = [
        score_message(
            message, role_weights, phase_weights, preferences, message_boosts, topic_boosts
        )
        for message in messages
    ]
    return sorted(
        scored,
        key=lambda message: (-message["score"], message["id"]),
    )
