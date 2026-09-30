# EverCurrent Digest

A role- and project-phase-aware Slack digest prototype for Project Atlas.

## Requirements

- Python 3.10+

## Batch 1

```bash
python3 demo.py
```

Expected output:

```text
Loaded 18 Slack messages.
```

## Batch 2

Inspect deterministic message tags and urgency:

```bash
python3 demo.py --show-tags
```

## Batch 3

Inspect role and phase weights:

```bash
python3 demo.py --role electrical_engineer --phase dvt --show-weights
```

## Batch 4

Show a personalized Top-5 with an explanation tag for every score:

```bash
python3 demo.py --role electrical_engineer --phase dvt --show-ranking
python3 demo.py --role supply_chain --phase dvt --show-ranking
```

## Batch 5

Generate the complete citation-backed Markdown digest:

```bash
python3 demo.py --role electrical_engineer --phase dvt
```

The generator receives at most five messages and copies their source text verbatim;
every bullet ends in a message citation such as `[M001]`.

## Batch 6

Apply persistent feedback and immediately see the before/after ranking and the new
digest (phase defaults to DVT for this command):

```bash
python3 demo.py --feedback M011:up --role electrical_engineer
python3 demo.py --feedback M006:down --role electrical_engineer
```

Feedback changes the relevant topic weights by `0.15` and stores a bounded explicit
item boost. Both are persisted in `data/preferences.json`; subsequent digest runs use
the learned values.

## Publish the demo to Slack

Create an Incoming Webhook for the Slack channel you want to demo in, then keep the
secret out of source control:

```bash
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'
python3 demo.py --role electrical_engineer --phase dvt --slack
```

The command prints the exact digest locally first and exits with an error unless Slack
accepts the POST. The webhook URL is read only from the environment and is never logged
or saved by this project.
