"""Read channel history from Slack's Web API for the live demo."""

from __future__ import annotations

import json
import os
import re
import ssl
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
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

    def __init__(self, token: str | None = None, cache_path: Path | None = None) -> None:
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        if not self.token:
            raise SlackClientError("SLACK_BOT_TOKEN is not available")
        self.cache_path = cache_path or Path(__file__).resolve().parents[1] / "data" / "runtime" / "cache.json"
        self.stale = False

    def fetch_messages(self, channel_id: str, limit: int = 100, simulate_failure: bool = False) -> list[dict]:
        self.stale = False
        last_error: SlackClientError | None = None
        if not simulate_failure:
            for attempt in range(3):
                try:
                    messages = self._fetch_once(channel_id, limit)
                    self._save_cache(channel_id, messages)
                    return messages
                except SlackClientError as error:
                    last_error = error
                    if attempt < 2:
                        time.sleep(0.2 * (attempt + 1))
        cached = self._read_cache().get(channel_id, {}).get("messages")
        if cached is not None:
            self.stale = True
            return cached
        reason = "Simulated Slack failure" if simulate_failure else str(last_error)
        raise SlackClientError(f"{reason}; no cached messages for channel {channel_id}")

    def _fetch_once(self, channel_id: str, limit: int) -> list[dict]:
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
        # Slack returns newest first. Keep the newest occurrence of each stable ID so
        # accidental repeated `/seed-atlas` calls cannot dominate the ranking.
        messages_by_id: dict[str, dict] = {}
        for raw in payload.get("messages", []):
            message = self._normalize_message(raw, channel_id)
            if message is not None:
                messages_by_id.setdefault(message["id"], message)
        return list(messages_by_id.values())

    def _read_cache(self) -> dict:
        if not self.cache_path.exists():
            return {}
        try:
            with self.cache_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as error:
            raise SlackClientError(f"Cache could not be read: {error}") from error
        return data if isinstance(data, dict) else {}

    def _save_cache(self, channel_id: str, messages: list[dict]) -> None:
        cache = self._read_cache()
        cache[channel_id] = {
            "fetched_at": datetime.now(UTC).isoformat(),
            "messages": messages,
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix="cache-", suffix=".json", dir=self.cache_path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(cache, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary, self.cache_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @classmethod
    def _normalize_message(cls, raw: dict, channel_id: str) -> dict | None:
        text = raw.get("text", "").strip()
        # Slack may serialize the 🌅 emoji as :sunrise:, so match the stable title
        # rather than an exact Markdown/emoji prefix. This prevents recursive digests.
        if not text or "EverCurrent Daily Digest" in text:
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
            "source_url": f"https://app.slack.com/archives/{channel_id}/p{raw['ts'].replace('.', '')}",
            "text": text,
        }
