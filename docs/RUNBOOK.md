# Runbook: install, run, test, and demo

All commands below start from the repository root unless a `cd` is shown. Use two terminal windows for the Slack demo: one keeps the app running; the other can run tests. This repository is a local prototype, not a hosted Slack service.

## 1. Prerequisites

- Python 3.11+ and `python3 -m pip`.
- Node.js 20+ and npm.
- A Slack workspace where you can install an app and post to a test channel.
- Either the Slack CLI, linked to an app, **or** a bot token and an app-level Socket Mode token. The CLI path is convenient for the existing Digest app; the token path works with a new app created from the included manifest. For macOS/Linux, follow Slack's [CLI installation guide](https://docs.slack.dev/tools/slack-cli/guides/installing-the-slack-cli-for-mac-and-linux/) and verify with `slack version`.

Do not commit `.env`, bot/app tokens, or webhook URLs. The repository ignores `.env` and `data/runtime/`.

## 2. Install dependencies

```bash
git clone https://github.com/shuwenhhh/DigestTool.git
cd DigestTool
python3 -m pip install -r requirements.txt
cd slack-app
npm ci
cd ..
```

`npm ci` uses the committed lockfile. If Python is managed by your OS and rejects a global install, create and activate a virtual environment first; run all later Python commands in that same environment.

## 3. Run without Slack first

```bash
python3 demo.py --role pm --phase dvt
python3 demo.py --role electrical_engineer --phase dvt --show-ranking
python3 demo.py --evaluate
```

The evaluator should report `Citation validity: 5/5` and `Faithfulness: 1.00` on the bundled 18-message corpus. This path needs no Slack credentials. It does not prove that the app is connected to Slack.

## 4A. Run the existing linked Digest app with Slack CLI

Use this if you have access to the existing Slack app `A0C5HTEUS5U` in the EverCurrent workspace. The command and flags are documented in Slack's [`slack run` reference](https://docs.slack.dev/tools/slack-cli/reference/commands/slack_run/). In terminal 1:

```bash
cd slack-app
slack login
slack run --app A0C5HTEUS5U --manifest-source=local
```

Run `slack login` only when not already signed in. Leave `slack run` running. The CLI supplies Slack credentials to the local Bolt process and watches JavaScript app files. If you do not have access to this app ID, use option 4B instead; cloning the repository alone does not grant access to someone else's Slack app.

## 4B. Run your own app with tokens

1. At [Slack app management](https://api.slack.com/apps), create an app **from an app manifest** using [`slack-app/manifest.json`](../slack-app/manifest.json), select your workspace, and install it.
2. In **Basic Information**, create an app-level token with `connections:write` and copy its `xapp-...` value. In **OAuth & Permissions**, copy the installed bot token (`xoxb-...`). The manifest enables Socket Mode, `/digest`, `/seed-atlas`, and the required public-channel bot scopes. See Slack's [Socket Mode guide](https://docs.slack.dev/tools/bolt-js/concepts/socket-mode/) for the token setup.
3. From the repository root, create `slack-app/.env` containing only these two lines (replace the placeholders with your actual values):

   ```text
   SLACK_APP_TOKEN=xapp-YOUR-APP-TOKEN
   SLACK_BOT_TOKEN=xoxb-YOUR-BOT-TOKEN
   ```

4. Start the app:

   ```bash
   cd slack-app
   npm start
   ```

`app.js` reads `.env` and starts Bolt in Socket Mode. The Python bridge inherits the bot token from this process. There is no Incoming Webhook requirement for `/digest`. Stop the process with Ctrl+C when finished.

## 5. Demo in Slack

1. Create or choose a **public** test channel, for example `#project-atlas`, and invite the app with `/invite @Digest`. The current manifest requests `channels:history`, not private-channel history.
2. Type `/seed-atlas` **as a Slack slash command**. Wait for the private confirmation. It posts any missing messages from the 18-message demo set; rerunning it skips IDs already present.
3. Run the following in the same channel:

   ```text
   /digest electrical_engineer dvt
   /digest supply_chain dvt
   /digest pm evt
   /digest pm pvt
   /digest pm dvt
   ```

4. Open a cited source ID in the Digest to verify it jumps to the original channel message. The Digest itself and its rating controls are visible only to the requesting user.
5. In one Digest, click 👍 **Useful** or 👎 **Not relevant** for an item. The button becomes selected and shows a private confirmation. Run the **same** `/digest role phase` command again to see the next ranking. Click the selected button again to undo, or click the opposite button to switch.

Rank changes depend on current channel history and previous votes; they are not hard-coded. A single vote now affects its item most, a specific topic moderately, and a broad category only slightly. If the channel has other messages or your profile already has feedback, your Top 5 may differ from another person's. The app reads up to the newest 100 channel messages per digest; keep the seeded updates within that window for the demo.

## 6. Verify the repository

In terminal 2, from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 demo.py --evaluate
cd slack-app
npm test
npm run lint
```

The automated tests use mocks and do not post to Slack. A successful local test run does not replace the live `/digest` check above.

## 7. Troubleshooting

| Symptom | Check |
| --- | --- |
| Slack says the command is unavailable | Confirm the app is installed in this workspace, the local process is running, and the manifest contains both slash commands. |
| Digest says no source messages were found | Run `/seed-atlas` in that channel, then `/digest` in the same channel. |
| `not_in_channel` or history read failure | Invite the app to the public test channel and confirm its `channels:history` scope. |
| `SLACK_BOT_TOKEN is not available` | Use `slack run` for the linked app or put `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `slack-app/.env` for `npm start`. |
| Old ranking still appears | Generate a **new** Digest; feedback updates the rating state immediately, while ranking is recalculated on the next command. |
| `⚠️ STALE DATA` appears | Slack history failed and the app used its last channel cache. Restore the connection before presenting the result as current. |

See [System design](SYSTEM_DESIGN.md) and [Algorithm](ALGORITHM.md) for implementation details.
