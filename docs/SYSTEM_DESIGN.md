# System design

EverCurrent Digest is a **local, single-workspace prototype**. A Slack Bolt app receives slash commands and private button actions through Socket Mode. Each request launches the Python bridge, which reads the invoking channel and returns a source-cited Top 5. There is no external database, hosted API, scheduler, or LLM in the current implementation.

## Components and data flow

```mermaid
flowchart TB
    subgraph Slack[Slack workspace]
        User[User]
        Channel[Public channel history]
        Private[Ephemeral Digest card]
    end

    subgraph Local[Local machine]
        Bolt["Bolt JS /digest, /seed-atlas, feedback"]
        Bridge["Python slack.bridge subprocess"]
        Reader["RealSlackClient: history, normalize, deduplicate"]
        Tagger["Tagger: tags, topic, urgency"]
        Ranker["Ranker: role × phase × user preference"]
        Generator["Generator: Top 5, sections, citations"]
        Profile[(Preferences JSON)]
        Cache[(Channel cache JSON)]
        Config[(Role and phase config)]
        Corpus[(18-message demo corpus)]
    end

    User -->|/digest| Bolt
    User -->|/seed-atlas| Bolt
    Corpus -->|missing seed IDs only| Bolt
    Bolt -->|post seed updates| Channel
    Bolt -->|spawn with channel, role, phase, user| Bridge
    Bridge --> Reader
    Reader <-->|conversations.history| Channel
    Reader <--> Cache
    Reader --> Tagger --> Ranker --> Generator --> Bridge
    Config --> Ranker
    Profile <--> Ranker
    Bridge -->|JSON response| Bolt --> Private --> User
    User -->|private thumbs up/down| Bolt
    Bolt -->|feedback request| Bridge
    Bridge -->|atomic profile update| Profile
```

The JavaScript service at [`slack-app/listeners/digest-service.js`](../slack-app/listeners/digest-service.js) invokes `python3 -m slack.bridge` with `execFile`; it does not build a shell command from user input. The bridge returns JSON. The UI translates cited Markdown links into Slack-formatted links and renders per-item rating buttons.

## Request and feedback sequence

```mermaid
sequenceDiagram
    actor U as Slack user
    participant S as Slack
    participant J as Bolt JS
    participant P as Python bridge
    participant H as Channel history
    participant F as Per-user profile

    U->>S: /digest pm dvt
    S->>J: Slash command via Socket Mode
    J->>S: Acknowledge
    J->>P: Run bridge(channel, pm, dvt, user ID)
    P->>H: Read latest public-channel messages
    H-->>P: Messages + timestamps
    P->>F: Read that user's PM profile
    P-->>J: Top 5 + cited digest + current votes
    J-->>U: Ephemeral Digest
    U->>S: Click Not relevant on M018
    S->>J: Button action
    J->>S: Acknowledge
    J->>P: Run bridge(..., M018, down)
    P->>F: Save toggled vote and bounded weights
    P-->>J: Rank movement + vote state
    J-->>U: Replace private card with selected button
    U->>S: /digest pm dvt again
    S->>J: New command
    J->>P: Recalculate with saved profile
    P-->>J: New ranking
    J-->>U: New ephemeral Digest
```

## State and boundaries

- **Source:** `RealSlackClient` calls Slack `conversations.history` with the bot token, reads up to the newest 100 messages, and retries failed reads twice. It excludes earlier Digest output to avoid self-summarization. Seeded `[M001]`-style IDs are deduplicated; ordinary messages get stable timestamp-based `S...` IDs and Slack permalinks.
- **Fallback:** A successful read atomically updates the per-channel JSON cache. If Slack later fails, the bridge uses cached messages and clearly prefixes the output with `⚠️ STALE DATA`. Without a cache, it fails instead of inventing a result.
- **Personalization:** Profiles are keyed by `Slack user ID:role`; votes change only that user's role profile. Slack feedback is private and stored in ignored `data/runtime/preferences.json`. Role and phase defaults are committed configuration files. Prior votes are migrated to current weights once, without discarding the vote.
- **Presentation:** The Top 5 is computed **before** section grouping. A message's `#rank` is its overall score position; display sections such as Critical and Schedule are grouping labels, not separate ranking pools. The cited text is copied from the source message, and each live citation links back to it.
- **Security/scope:** Tokens come from the Slack CLI environment or local `.env`, not the repository. The current manifest requests `channels:history`, `chat:write`, and `commands`; the runbook therefore uses a public channel with the app invited. The JSON store is local and not appropriate for concurrent production workers.

## Design choices and limitations

| Choice | Why | Limit |
| --- | --- | --- |
| Deterministic rules instead of an LLM | Easy to explain, reproduce, and check for exact-source faithfulness. | Cannot paraphrase or infer facts across messages. |
| Strongest tag score | One message with several tags is not rewarded simply for matching more keywords. | Secondary tags can still change the winning tag after feedback. |
| Item + specific topic + tiny broad-tag feedback | Makes one vote visible without suppressing a whole category. | Repeated votes accumulate; this is not a learned semantic model. |
| Ephemeral Digest and ratings | Feedback stays personal; colleagues do not see a negative rating on their message. | An ephemeral card is not a shared team artifact. |
| Local JSON persistence | Simple, auditable demo state. | Replace with a transactional store for multiple workers/users at scale. |

The implementation of the scoring and feedback bounds is documented in [Algorithm](ALGORITHM.md). The executable setup and Slack demo are in [Runbook](RUNBOOK.md).
