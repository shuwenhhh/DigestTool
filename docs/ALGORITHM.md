# Ranking and feedback algorithm

This is the algorithm implemented by [`digest/tagger.py`](../digest/tagger.py), [`digest/ranker.py`](../digest/ranker.py), [`digest/personalization.py`](../digest/personalization.py), and [`digest/generator.py`](../digest/generator.py). It is deterministic: the same source messages, role, phase, and saved profile yield the same ordering.

## 1. Normalize and tag

The Slack reader strips the seed wrapper from demo messages, ignores earlier EverCurrent Digest output, deduplicates stable seed IDs, and adds each source message's Slack permalink. The tagger then assigns zero or more of these labels by keyword: `BOM_CHANGE`, `ECO`, `BLOCKER`, `SCHEDULE`, `TEST_RESULT`, `DECISION`, `SUPPLY_CHAIN`, `QUALITY`, and `DESIGN_CHANGE`.

It also computes urgency in `[0, 1]` from explicit phrases such as `failed`, `blocked`, and `due Friday`; a message with no urgency phrase gets `0.18`. A narrow recognized topic (for example `sensor-noise`, `thermal-validation`, `can-bus`, `firmware-freeze`, or `dvt-exit-review`) is marked **specific**. Otherwise its first tag becomes a **broad** topic such as `schedule`; untagged messages use `general`.

## 2. Score every message

For message `m`, role `r`, phase `p`, and user `u`:

```text
tag_relevance(m, r, p, u) = max over tag t in tags(m) of
    role_weight[r,t] × phase_weight[p,t] × user_tag_weight[u,r,t]

score(m, r, p, u) = tag_relevance
                    + 0.30 × urgency(m)
                    + item_boost[u,r,m.id]
                    + topic_boost[u,r,m.topic]
```

Missing role, phase, or user tag weights default to `1.0`. An untagged message gets tag relevance `0`. Scores are rounded to four decimals. Messages sort by **descending score**, then **ascending ID** for deterministic ties. The top five enter the Digest. The `#1`–`#5` labels are these **overall positions**; subsequent Critical, Schedule, and Test Results headings only group the selected items for reading. Within each heading, items retain their relative overall order.

Role weights live in [`config/roles.json`](../config/roles.json) and phase weights in [`config/phases.json`](../config/phases.json). For example, PM · DVT gives `BLOCKER` a base relevance of `1.5 × 1.3 = 1.95` before urgency or feedback. A PM · EVT or PM · PVT run uses different phase multipliers and can produce a different Top 5 from the same 18 messages.

## 3. Apply private feedback

Each vote belongs to one `Slack user ID:role` profile. A vote has three layers:

| Signal | One 👍 | One 👎 | Affects |
| --- | ---: | ---: | --- |
| Each tag on the rated message | `+0.01` multiplier | `−0.01` multiplier | Other messages sharing that tag, very slightly |
| Rated message ID | `+0.15` score | `−0.15` score | That message only |
| Broad topic | `+0.04` score | `−0.04` score | Messages with that broad topic |
| Specific topic | `+0.15` score | `−0.15` score | Messages with that narrow topic |

The topic row is **either** broad **or** specific, not both. Tag multipliers are clipped to `[0.4, 1.6]`; item boosts to `[−0.45, +0.45]`; topic boosts to `[−1.05, +1.05]`. Raw, unclipped values are retained so undo still works after saturation. Clicking an already-selected button removes that vote; clicking the opposite button switches it. Existing stored votes are migrated once when scoring rules change; the feedback history is not discarded.

For the bundled PM · DVT case, a 👎 on M018 (`dvt-exit-review`) lowers M018 most. The other DVT blocker messages only inherit the tiny `BLOCKER` tag multiplier change; they do **not** all inherit an old, generic `blocker` topic penalty. On the fresh bundled corpus, M018 moves from `#4` to `#5`, while M001, M014, and M013 remain `#1`–`#3`. Prior votes or different channel history can change exact positions.

## 4. Generate and validate

The generator takes **only** the ranked Top 5 and copies each source text verbatim into its display section. A live Slack source ends with a clickable `[M001]` or `[S...]` citation pointing to its original message; the offline mock has plain IDs because it has no Slack URLs. The evaluator checks each bullet's exact source text, ID, and URL (when present):

```text
faithfulness = valid_cited_bullets / total_digest_bullets
```

`python3 demo.py --evaluate` is the repeatable local check. A score of `1.00` means the rendered bullets match their cited inputs, **not** that the ranking is objectively perfect or that every important update was selected. Relevance should be evaluated separately with human-labeled examples and metrics such as precision@5 or recall@5; those datasets are not part of this prototype.

## 5. Reproduce a ranking

```bash
python3 demo.py --role pm --phase dvt --show-weights
python3 demo.py --role pm --phase dvt --show-ranking
python3 demo.py --show-tags
python3 demo.py --evaluate
```

`--show-ranking` reads the local CLI profile, not a specific Slack user's private profile. To see the latter, run `/digest pm dvt` as that user in Slack. See the [runbook](RUNBOOK.md) for end-to-end steps.
