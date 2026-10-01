# EverCurrent Digest

A runnable, role- and project-phase-aware Slack digest prototype for Project Atlas. It ranks real channel updates, produces a source-cited Top 5, and adapts each user's future digests from 👍/👎 feedback.

## 1. Problem

Project updates arrive as a noisy Slack stream. An Electrical Engineer, Supply Chain lead, and PM need different highlights; priorities also change between EVT (engineering validation), DVT (design validation), and PVT (production validation). The prototype makes those choices explicit and testable.

## 2. Demo

Requirements: Python 3.10+, Node.js, the [Slack CLI](https://docs.slack.dev/tools/slack-cli/), and access to the linked Digest app/workspace. Install dependencies once:

```bash
python3 -m pip install -r requirements.txt
cd digest-1 && npm install && cd ..
```

For the live demo, sign in with `slack login` if needed and keep the local Socket Mode app running in a terminal:

```bash
cd digest-1
slack run --app A0C5HTEUS5U --manifest-source=local
```

In the Slack channel you want to use (for example `#project-atlas`), invite the app with `/invite @Digest`. Then:

```text
/seed-atlas
/digest electrical_engineer dvt
/digest supply_chain dvt
/digest pm evt
/digest pm pvt
```

`/seed-atlas` adds the 18 sample updates to that channel. It skips seed IDs already present, so repeating it does not repost them. The seeded messages use today's Slack timestamps; they are demo history, not backdated conversations. `/digest` reads that channel's actual history and posts a digest visible to the channel, with a 👍 Useful and 👎 Not relevant button for each selected item. Click a button to save *your* preference and immediately post a reranked digest. The private confirmation reports the item's before/after rank; its position may stay the same if it was already at the top or the bounded feedback is insufficient to pass another item. Keep `slack run` running throughout the recording. No webhook is required for this path.

For a deterministic local demo without Slack:

```bash
python3 demo.py --role electrical_engineer --phase dvt
python3 demo.py --role supply_chain --phase dvt
python3 demo.py --role pm --phase evt
python3 demo.py --role pm --phase pvt
python3 demo.py --evaluate
```

The optional Incoming Webhook publisher is separate from the interactive Slack app: set `SLACK_WEBHOOK_URL` in your environment and run `python3 demo.py --role electrical_engineer --phase dvt --slack`. Never commit tokens or webhook URLs.

## 3. Architecture

```text
Slack channel history ─┐
18-message mock data ───┴─> Normalize/dedupe ─> Tag + urgency
                                                │
Role weights ───────────────┐                   ▼
Phase weights ──────────────┼──────────────> Rank messages ─> Top 5
Per-user preferences ───────┘                        │           │
                                                     │           ▼
Slack 👍/👎 ─> preference update ─────────────────────┘    Cited digest ─> Slack
                                                          │
                                                          ▼
                                                Citation/faithfulness check
```

`digest-1/` is the JavaScript Slack Bolt app. It calls `slack/bridge.py` as a local Python process; the bridge uses `slack/client.py` and the `digest/` tagging, ranking, generation, and personalization modules. `demo.py` exercises the same engine from the terminal.

## 4. Message Tagging

The deterministic tagger recognizes `BOM_CHANGE`, `ECO`, `BLOCKER`, `SCHEDULE`, `TEST_RESULT`, `DECISION`, `SUPPLY_CHAIN`, `QUALITY`, and `DESIGN_CHANGE`, and assigns urgency from 0 to 1. Inspect all 18 tagged examples with `python3 demo.py --show-tags`.

## 5. Personalization

`config/roles.json` and `config/phases.json` define role and phase weights. For a message's strongest tag, the ranking score is `role_weight × phase_weight × preference_weight + 0.3 × urgency + explicit_item_boost`. Inspect weights with `python3 demo.py --role electrical_engineer --phase dvt --show-weights`; inspect the ordered IDs and reasons with `--show-ranking`. The mock data and phase weights make both role and EVT/DVT/PVT differences visible.

## 6. Adaptive Feedback

A 👍 or 👎 changes the selected item's tag affinities by ±0.15 and its explicit boost by ±0.15, within bounds. Interactive Slack profiles are keyed by Slack user ID plus role, so one person's click does not change another person's ranking. Feedback is persisted in ignored `data/runtime/preferences.json`; `data/preferences.json` provides only initial values. The local CLI feedback demo is `python3 demo.py --feedback M011:up --role electrical_engineer`.

## 7. Grounding / Citations

The generator only receives the five ranked source messages and copies each update's text verbatim. Every digest bullet ends in a source ID such as `[M001]` (or an `S...` ID for an ordinary Slack message). This is template-based generation, not an LLM making unsupported claims. The evaluator checks both citation existence and exact source-text match. The real Slack reader excludes prior EverCurrent digests to prevent recursive summaries and deduplicates repeated seed IDs.

## 8. Failure Handling

History reads retry twice after the initial attempt. A successful read is saved per channel in ignored `data/runtime/cache.json`. If Slack remains unavailable, the latest cached channel data is used and the digest is marked `⚠️ STALE DATA`. Without a cache, generation fails clearly instead of silently presenting invented or empty results. Once a real channel has been fetched successfully, simulate this path with:

```bash
python3 demo.py --slack-channel CHANNEL_ID --role electrical_engineer --phase dvt --simulate-slack-failure
```

This requires `SLACK_BOT_TOKEN` in the environment; `slack run` supplies it to the Bolt process, not necessarily your separate terminal. Use the app's own local process for a live Slack demo.

## 9. Evaluation

```bash
python3 -m unittest discover -s tests -v
cd digest-1 && npm test && npm run lint
python3 demo.py --evaluate
```

The bundled mock set should report `Citation validity: 5/5` and `Faithfulness: 1.00`. Tests cover the role/phase differences, feedback rank movement and user isolation, Slack normalization, cache fallback, button payloads, and idempotent seeding.

## 10. Production Considerations

This is a single-machine take-home prototype. For production, replace JSON files with a persistent per-user profile and channel cache store (for example PostgreSQL), add channel allowlists and retention/deletion controls, use cursor-based incremental ingestion, and handle Slack rate limits plus a background job queue. Explicitly review Slack scopes and permissions for private channels. Add monitoring, structured non-secret logs, and evaluation against a labeled set of relevance and faithfulness examples. The current rule tagger and template generator are deliberately explainable; an LLM layer would require grounding and citation validation before publishing.
