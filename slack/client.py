"""Read channel history from Slack's Web API for the live demo."""

from __future__ import annotations

import json
import os
import re
import ssl
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi


class SlackClientError(RuntimeError):
    """Raised when Slack history cannot be retrieved."""


class MockSlackClient:
    """Kept as the local-data source for deterministic tests and demos."""

    def fetch_messages(self, messages: list[dict]) -> list[dict]:
        return messages


class RealSlackClient:
    """Fetch channel history using the bot token injected by `slack run`."""

    HISTORY_URL = "https://slack.com/api/conversations.history"
    SEEDED_MESSAGE = re.compile(
        r"^\[(?P<id>M\d{3})\]\s+\[(?P<role>[^·\]]+)\s+·\s+(?P<author>[^\]]+)\]\s*(?P<text>.*)$",
        re.DOTALL,
    )

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        if not self.token:
            raise SlackClientError("SLACK_BOT_TOKEN is not available")

    def fetch_messages(self, channel_id: str, limit: int = 100) -> list[dict]:
        query = urlencode({"channel": channel_id, "limit": limit})
        request = Request(
            f"{self.HISTORY_URL}?{query}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            with urlopen(request, timeout=10, context=context) as response:
                payload = json.load(response)
        except HTTPError as error:
            raise SlackClientError(f"Slack returned HTTP {error.code}") from error
        except URLError as error:
            raise SlackClientError(f"Could not reach Slack: {error.reason}") from error

        if not payload.get("ok"):
            raise SlackClientError(payload.get("error", "Unknown Slack API error"))
        return [
            message
            for raw in payload.get("messages", [])
            if (message := self._normalize_message(raw, channel_id)) is not None
        ]

    @classmethod
    def _normalize_message(cls, raw: dict, channel_id: str) -> dict | None:
        text = raw.get("text", "").strip()
        # Do not ingest a prior generated digest as if it were a source update.
        if not text or text.startswith("# 🌅 EverCurrent Daily Digest"):
            return None
        seeded = cls.SEEDED_MESSAGE.match(text)
        if seeded:
            parts = seeded.groupdict()
            message_id = parts["id"]
            role = parts["role"].strip()
            author = parts["author"].strip()
            text = parts["text"].strip()
        else:
            message_id = f"S{raw['ts'].replace('.', '')}"
            role = "Slack participant"
            author = raw.get("username") or raw.get("user") or "Unknown"
        timestamp = datetime.fromtimestamp(float(raw["ts"]), tz=UTC).isoformat()
        return {
            "id": message_id,
            "channel": channel_id,
            "author": author,
            "role": role,
            "timestamp": timestamp,
            "text": text,
        }
