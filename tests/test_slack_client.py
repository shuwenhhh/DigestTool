import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from slack.client import RealSlackClient, SlackClientError


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return io.StringIO(json.dumps(self.payload))

    def __exit__(self, *_args) -> None:
        return None


class RealSlackClientTests(unittest.TestCase):
    def test_normalizes_seeded_messages_and_ignores_old_digests(self) -> None:
        payload = {
            "ok": True,
            "messages": [
                {
                    "ts": "1760000000.000100",
                    "text": "[M001] [Electrical Engineer · Sarah]\nPCB failed validation.",
                },
                {
                    "ts": "1760000001.000100",
                    "text": "# 🌅 EverCurrent Daily Digest\nold output",
                },
                {
                    "ts": "1760000002.000100",
                    "text": ":sunrise: EverCurrent Daily Digest\nold output",
                },
                {
                    "ts": "1750000000.000100",
                    "text": "[M001] [Electrical Engineer · Sarah]\nOlder duplicate.",
                },
            ],
        }
        with patch("slack.client.urlopen", return_value=_Response(payload)):
            messages = RealSlackClient(token="xoxb-test").fetch_messages("C123")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["id"], "M001")
        self.assertEqual(messages[0]["author"], "Sarah")
        self.assertEqual(messages[0]["text"], "PCB failed validation.")
        self.assertEqual(
            messages[0]["source_url"],
            "https://app.slack.com/archives/C123/p1760000000000100",
        )

    def test_retries_then_uses_cached_channel_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "cache.json"
            client = RealSlackClient(token="xoxb-test", cache_path=cache_path)
            payload = {"ok": True, "messages": [{"ts": "1760000000.000100", "text": "[M001] [PM · Ava]\nBuild scheduled."}]}
            with patch("slack.client.urlopen", return_value=_Response(payload)):
                fresh = client.fetch_messages("C123")
            self.assertFalse(client.stale)
            with patch.object(client, "_fetch_once", side_effect=SlackClientError("offline")) as fetch:
                with patch("slack.client.time.sleep"):
                    cached = client.fetch_messages("C123")
            self.assertEqual(fetch.call_count, 3)
            self.assertTrue(client.stale)
            self.assertEqual(cached, fresh)
