"""JSON bridge between the Slack Bolt app and the Python digest engine."""

from __future__ import annotations

import argparse
import json

from digest.config_loader import load_phase_weights, load_role_weights
from digest.generator import generate_digest
from digest.personalization import apply_feedback, load_preferences, role_preferences
from digest.ranker import rank_messages
from digest.tagger import tag_messages
from slack.client import RealSlackClient, SlackClientError


def build_digest(
    channel: str,
    role: str,
    phase: str,
    user: str,
    feedback_id: str | None = None,
    direction: str | None = None,
    simulate_failure: bool = False,
) -> dict:
    client = RealSlackClient()
    messages = client.fetch_messages(channel, simulate_failure=simulate_failure)
    if not messages:
        raise ValueError("No source messages found. Run /seed-atlas in this channel first.")
    tagged = tag_messages(messages)
    role_name, role_weights = load_role_weights(role)
    phase_name, phase_weights = load_phase_weights(phase)
    profile_key = f"{user}:{role}"

    def rank() -> list[dict]:
        preferences, boosts = role_preferences(load_preferences(), profile_key)
        return rank_messages(tagged, role_weights, phase_weights, preferences, boosts)

    before = rank()
    movement = None
    if feedback_id:
        target = next((item for item in tagged if item["id"] == feedback_id), None)
        if target is None:
            raise ValueError(f"Message {feedback_id} is no longer in this channel's history")
        if direction not in {"up", "down"}:
            raise ValueError("Feedback must be up or down")
        before_rank = next(i for i, item in enumerate(before, 1) if item["id"] == feedback_id)
        apply_feedback(profile_key, target, direction)
        ranked = rank()
        after_rank = next(i for i, item in enumerate(ranked, 1) if item["id"] == feedback_id)
        movement = {"id": feedback_id, "direction": direction, "before": before_rank, "after": after_rank}
    else:
        ranked = before

    top = ranked[:5]
    digest = generate_digest(top, role_name, phase_name)
    if client.stale:
        digest = (
            "⚠️ STALE DATA — Slack is currently unavailable. "
            "Digest generated from the latest cached messages.\n\n" + digest
        )
    return {
        "digest": digest,
        "role": role,
        "phase": phase,
        "stale": client.stale,
        "source_count": len(messages),
        "top": [{"id": item["id"], "text": item["text"], "score": item["score"]} for item in top],
        "movement": movement,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--feedback-id")
    parser.add_argument("--direction", choices=["up", "down"])
    parser.add_argument("--simulate-slack-failure", action="store_true")
    args = parser.parse_args()
    try:
        result = build_digest(
            args.channel, args.role, args.phase, args.user,
            args.feedback_id, args.direction, args.simulate_slack_failure,
        )
    except (SlackClientError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
