import io
import json
import unittest
from unittest.mock import patch

from slack.client import RealSlackClient


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
            ],
        }
        with patch("slack.client.urlopen", return_value=_Response(payload)):
            messages = RealSlackClient(token="xoxb-test").fetch_messages("C123")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["id"], "M001")
        self.assertEqual(messages[0]["author"], "Sarah")
        self.assertEqual(messages[0]["text"], "PCB failed validation.")
