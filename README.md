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

`/seed-atlas` adds the 18 sample updates to that channel. It skips seed IDs already present, so repeating it does not repost them. The seeded messages use today's Slack timestamps; they are demo history, not backdated conversations. `/digest` reads that channel's actual history and sends a **personal, only-visible-to-you** Digest in Slack. Each item shows its **overall rank** (for example, `#3`) even though items are grouped under Critical, Test Results, etc. Each citation links to the original source message, but feedback stays on the Digest: click 👎 on M007, see the selected button and a concise private rank-change confirmation in the same card, then run `/digest electrical_engineer dvt` again to preview the next ranking. The next card explains the actual M007 outcome (for example, that it left the Top 5) and shows a `Tuned by your feedback` cue. Click the selected button again to undo, or the opposite button to switch. If a rated item falls out of the Top 5, its rating control remains available below the list for undo. This preview uses the current channel history with updated preferences; it does **not** pretend to have tomorrow's messages. Keep `slack run` running throughout the recording. No webhook is required for this path.

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
Private Digest 👍/👎 ─> preference update ────────────┘    Cited digest ─> Slack
                                                          │
                                                          ▼
                                                Citation/faithfulness check
```

`digest-1/` is the JavaScript Slack Bolt app. It calls `slack/bridge.py` as a local Python process; the bridge uses `slack/client.py` and the `digest/` tagging, ranking, generation, and personalization modules. `demo.py` exercises the same engine from the terminal.

## 4. Message Tagging

The deterministic tagger recognizes `BOM_CHANGE`, `ECO`, `BLOCKER`, `SCHEDULE`, `TEST_RESULT`, `DECISION`, `SUPPLY_CHAIN`, `QUALITY`, and `DESIGN_CHANGE`, and assigns urgency from 0 to 1. Inspect all 18 tagged examples with `python3 demo.py --show-tags`.

## 5. Personalization

`config/roles.json` and `config/phases.json` define role and phase weights. For a message's strongest tag, the ranking score is `role_weight × phase_weight × preference_weight + 0.3 × urgency + explicit_item_boost + topic_boost`. Inspect weights with `python3 demo.py --role electrical_engineer --phase dvt --show-weights`; inspect the ordered IDs and reasons with `--show-ranking`. The mock data and phase weights make both role and EVT/DVT/PVT differences visible.

## 6. Adaptive Feedback

A 👍 or 👎 changes the selected item's tag affinities by only ±0.03, its explicit boost by ±0.15, and its specific topic boost by ±0.15, within bounds. Distinct blocker topics (thermal validation, CAN bus, firmware freeze, DVT exit review) prevent a 👎 on one blocker from demoting the entire DVT blocker category. M007 is classified as `sensor-noise`, so its topic feedback also affects future sensor-noise updates. Existing votes are migrated to the narrower weights once, without clearing a user's feedback. Repeating the same vote undoes it; clicking the opposite vote switches it. Interactive Slack profiles are keyed by Slack user ID plus role, so one person's click does not change another person's ranking. The private Digest updates its selected state immediately, while ranking changes appear on the next `/digest`. Feedback is persisted in ignored `data/runtime/preferences.json`; `data/preferences.json` provides only initial values. The local CLI feedback demo is `python3 demo.py --feedback M011:up --role electrical_engineer`.

## 7. Grounding / Citations

The generator only receives the five ranked source messages and copies each update's text verbatim. Every digest bullet ends in a source ID such as `[M001]` (or an `S...` ID for an ordinary Slack message). For live Slack history, that ID is a clickable permalink to the original message. Offline mock messages have no Slack URL, so their IDs remain plain references. This is template-based generation, not an LLM making unsupported claims. The evaluator checks citation existence, exact source-text match, and—for live sources—that the linked URL matches the cited source. The real Slack reader excludes prior EverCurrent digests to prevent recursive summaries and deduplicates repeated seed IDs.

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
