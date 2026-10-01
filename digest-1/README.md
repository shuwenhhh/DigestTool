# Digest Slack app

This is the Bolt for JavaScript Socket Mode frontend for [EverCurrent Digest](../README.md). It registers `/digest`, `/seed-atlas`, and private per-item feedback buttons. It launches [`slack.bridge`](../slack/bridge.py) as a Python subprocess; the Python engine fetches channel history, ranks messages, and returns a source-cited Digest.

For complete installation, Slack app configuration, commands to run, demo steps, and troubleshooting, use the repository [runbook](../docs/RUNBOOK.md). For design and scoring details, see [system design](../docs/SYSTEM_DESIGN.md) and [algorithm](../docs/ALGORITHM.md).

From this directory, after installing the root Python requirements and running `npm ci`, start one of these modes:

```bash
# Existing linked Digest app, when the Slack CLI and app access are available:
slack run --app A0C5HTEUS5U --manifest-source=local

# Your own app, after creating a local .env with SLACK_BOT_TOKEN and SLACK_APP_TOKEN:
npm start
```

Run `npm test` and `npm run lint` here. Never commit the local `.env` or credentials.
