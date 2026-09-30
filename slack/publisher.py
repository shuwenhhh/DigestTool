"""Publish a generated digest to a real Slack Incoming Webhook."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SlackPublishError(RuntimeError):
    pass


def build_payload(digest: str, role_name: str, phase_name: str) -> dict:
    return {
        "text": f"🌅 EverCurrent Daily Digest — {role_name} · {phase_name}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🌅 EverCurrent Daily Digest",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*{role_name}* · *{phase_name}*"}
                ],
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": digest}},
        ],
    }


def publish_digest(
    webhook_url: str,
    digest: str,
    role_name: str,
    phase_name: str,
    timeout: float = 10.0,
) -> None:
    if not webhook_url.startswith(("https://", "http://")):
        raise SlackPublishError("Webhook URL must start with http:// or https://")
    body = json.dumps(build_payload(digest, role_name, phase_name)).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            if response.status < 200 or response.status >= 300:
                raise SlackPublishError(
                    f"Slack returned HTTP {response.status}: {response_body}"
                )
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise SlackPublishError(f"Slack returned HTTP {error.code}: {details}") from error
    except URLError as error:
        raise SlackPublishError(f"Could not reach Slack: {error.reason}") from error
