#!/usr/bin/env python3
"""EverCurrent personalized digest demo."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from digest.config_loader import load_phase_weights, load_role_weights
from digest.generator import generate_digest
from digest.personalization import apply_feedback, load_preferences, role_preferences
from digest.ranker import rank_messages
from digest.tagger import tag_messages
from slack.client import RealSlackClient, SlackClientError
from slack.publisher import SlackPublishError, publish_digest


ROOT = Path(__file__).resolve().parent
MESSAGES_PATH = ROOT / "data" / "mock_messages.json"


def load_messages(slack_channel: str | None = None) -> list[dict]:
    if slack_channel:
        return RealSlackClient().fetch_messages(slack_channel)
    with MESSAGES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--show-tags",
        action="store_true",
        help="Print rule-based tags and urgency for every message.",
    )
    parser.add_argument("--role", help="Role key, for example electrical_engineer.")
    parser.add_argument("--phase", help="Project phase key, for example dvt.")
    parser.add_argument(
        "--show-weights",
        action="store_true",
        help="Print the selected role and phase weights.",
    )
    parser.add_argument(
        "--show-ranking",
        action="store_true",
        help="Print the personalized message ranking.",
    )
    parser.add_argument(
        "--feedback",
        metavar="MESSAGE_ID:up|down",
        help="Persist feedback, rerank, and regenerate the digest.",
    )
    parser.add_argument(
        "--slack",
        action="store_true",
        help="Publish the generated digest through SLACK_WEBHOOK_URL.",
    )
    parser.add_argument(
        "--slack-channel",
        metavar="CHANNEL_ID",
        help="Generate from real Slack channel history (requires SLACK_BOT_TOKEN).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        messages = load_messages(args.slack_channel)
    except SlackClientError as error:
        raise SystemExit(f"Slack history fetch failed: {error}") from error
    tagged_messages = tag_messages(messages)
    print(f"Loaded {len(messages)} Slack messages.")
    if args.show_tags:
        for message in tagged_messages:
            print(f"\n{message['id']}")
            print(f"Tags: {', '.join(message['tags'])}")
            print(f"Urgency: {message['urgency']:.2f}")
    if args.show_weights:
        if not args.role or not args.phase:
            raise SystemExit("--show-weights requires both --role and --phase")
        role_name, role_weights = load_role_weights(args.role)
        phase_name, phase_weights = load_phase_weights(args.phase)
        print(f"\nLoaded profile: {role_name} + {phase_name}")
        print("Role weights:")
        for tag, weight in role_weights.items():
            print(f"  {tag}: {weight:.2f}")
        print("Phase weights:")
        for tag, weight in phase_weights.items():
            print(f"  {tag}: {weight:.2f}")
    if args.show_ranking:
        if not args.role or not args.phase:
            raise SystemExit("--show-ranking requires both --role and --phase")
        role_name, role_weights = load_role_weights(args.role)
        phase_name, phase_weights = load_phase_weights(args.phase)
        preferences, message_boosts = role_preferences(
            load_preferences(), args.role
        )
        ranked = rank_messages(
            tagged_messages,
            role_weights,
            phase_weights,
            preferences,
            message_boosts,
        )
        print(f"\n{role_name} · {phase_name} Top 5")
        for index, item in enumerate(ranked[:5], start=1):
            print(
                f"{index}. {item['id']}  score={item['score']:.2f}  "
                f"reason={item['score_tag']}"
            )
    if args.feedback:
        if not args.role:
            raise SystemExit("--feedback requires --role")
        if not args.phase:
            args.phase = "dvt"
        try:
            message_id, direction = args.feedback.split(":", 1)
        except ValueError as error:
            raise SystemExit("Feedback must look like M011:up or M006:down") from error
        message_lookup = {message["id"]: message for message in tagged_messages}
        if message_id not in message_lookup:
            raise SystemExit(f"Unknown message ID: {message_id}")
        role_name, role_weights = load_role_weights(args.role)
        phase_name, phase_weights = load_phase_weights(args.phase)
        stored = load_preferences()
        before_preferences, before_boosts = role_preferences(stored, args.role)
        before = rank_messages(
            tagged_messages,
            role_weights,
            phase_weights,
            before_preferences,
            before_boosts,
        )
        before_position = next(
            index for index, item in enumerate(before, start=1) if item["id"] == message_id
        )
        changes = apply_feedback(
            args.role, message_lookup[message_id], direction
        )
        after_preferences, after_boosts = role_preferences(
            load_preferences(), args.role
        )
        after = rank_messages(
            tagged_messages,
            role_weights,
            phase_weights,
            after_preferences,
            after_boosts,
        )
        after_position = next(
            index for index, item in enumerate(after, start=1) if item["id"] == message_id
        )
        icon = "👍" if direction == "up" else "👎"
        print(f"\nBefore feedback: {message_id} ranked #{before_position}")
        print(f"{icon} {message_id}")
        for tag, old, new in changes:
            print(f"{tag}: {old:.2f} → {new:.2f}")
        print(f"After feedback: {message_id} ranked #{after_position}\n")
        print(generate_digest(after[:5], role_name, phase_name))
        return
    if args.role and args.phase and not (args.show_weights or args.show_ranking):
        role_name, role_weights = load_role_weights(args.role)
        phase_name, phase_weights = load_phase_weights(args.phase)
        preferences, message_boosts = role_preferences(
            load_preferences(), args.role
        )
        ranked = rank_messages(
            tagged_messages,
            role_weights,
            phase_weights,
            preferences,
            message_boosts,
        )
        digest = generate_digest(ranked[:5], role_name, phase_name)
        print()
        print(digest)
        if args.slack:
            webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
            if not webhook_url:
                raise SystemExit(
                    "SLACK_WEBHOOK_URL is not set. Add your Slack Incoming Webhook "
                    "to the environment and rerun the command."
                )
            try:
                publish_digest(webhook_url, digest, role_name, phase_name)
            except SlackPublishError as error:
                raise SystemExit(f"Slack publish failed: {error}") from error
            print("\nPublished digest to Slack.")


if __name__ == "__main__":
    main()
