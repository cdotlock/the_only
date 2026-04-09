# Phase 6: Post-Ritual Reflection

> **When to read**: After Phase 5 Deliver passes its gate.

(Deep references: `references/context_engine.md` for full three-tier memory architecture, `references/knowledge_graph.md` for graph structure/visualization/decay, `references/mesh_network.md` for full Nostr protocol and CLI.)

---

## Purpose

Update all persistent state so the next ritual benefits from what this one learned.

---

## Steps

### 6.1 Episodic Update

Append one entry to `the_only_episodic.json` (FIFO 50 entries). Include every field:

```bash
python3 scripts/memory_io.py --action append-episodic --data '{
  "ritual_id": 48,
  "timestamp": "2026-04-07T09:00:00Z",
  "items_delivered": 5,
  "avg_quality_score": 7.8,
  "categories": {"tech": 3, "philosophy": 1, "serendipity": 1},
  "engagement": {
    "item_1": {"score": 1, "signal": "opened", "topic": "edge computing"},
    "item_3": {"score": 3, "signal": "replied", "topic": "neural arch search"}
  },
  "sources_used": ["hn", "arxiv", "aeon"],
  "sources_failed": [],
  "narrative_theme": "scaling laws and their limits",
  "synthesis_styles": {"deep_analysis": 3, "contrarian": 1, "cross_domain": 1},
  "self_notes": "User reaction on item 3 suggests interest in novel architectures beyond transformers",
  "ritual_type": "deep_dive",
  "type_reason": "storyline AI reasoning at 5 rituals"
}'
```

**Field reference:**

| Field | Type | Description |
|---|---|---|
| `ritual_id` | int | Sequential ritual number |
| `timestamp` | ISO 8601 | Ritual completion time |
| `items_delivered` | int | Count of items delivered |
| `avg_quality_score` | float | Mean composite quality score across items |
| `categories` | object | Category -> count mapping for delivered items |
| `engagement` | object | Per-item engagement signals (score 0-5, signal type, topic) |
| `sources_used` | string[] | Source identifiers that contributed items |
| `sources_failed` | string[] | Sources that were attempted but failed |
| `narrative_theme` | string | The throughline connecting delivered items |
| `synthesis_styles` | object | Style -> count mapping (deep_analysis, contrarian, cross_domain, etc.) |
| `self_notes` | string | Free-form observations that don't fit structured fields |
| `ritual_type` | string | The ritual type used (standard, deep_dive, flash, explorer, etc.) |
| `type_reason` | string | Why this type was selected |

### 6.2 Ritual Log

Append to `ritual_log.jsonl`.

### 6.3 Knowledge Graph Update

For each delivered item, extract concepts and relations, then ingest:

```bash
python3 scripts/knowledge_graph.py --action ingest --data '{
  "ritual_id": 48,
  "items": [
    {
      "title": "Why Reasoning in LLMs is Harder Than We Thought",
      "concepts": ["reasoning", "chain_of_thought", "planning", "llm_limitations"],
      "relations": [
        {"source": "chain_of_thought", "target": "reasoning", "relation": "enables"},
        {"source": "llm_limitations", "target": "planning", "relation": "contradicts"}
      ],
      "domain": "machine_learning",
      "mastery_signals": {"reasoning": "familiar", "llm_limitations": "introduced"}
    }
  ]
}'
```

**Concept extraction rules:**

- Extract **3-6 concepts per article** -- transferable ideas, not keywords. "Attention mechanism" yes, "Figure 3" no.
- Use consistent naming: prefer established terms over article-specific jargon.
- Include **at least 1 relation per article** connecting to existing graph concepts. This is what builds the cross-ritual web.
- Set `mastery_signals` based on how deeply the article treated each concept:
  - `introduced` -- concept appeared but was not the focus
  - `familiar` -- concept was explained or discussed substantively
  - `understood` -- user engaged deeply (engagement score 3+)
  - `mastered` -- user discussed, acted on, or taught this concept (engagement score 4-5)

**Relation types:** `related_to`, `component_of`, `enables`, `contradicts`, `evolves_from`, `analogous_to`, `applied_in`.

### 6.4 Maintenance Trigger Check

Adaptive, not fixed cadence. Evaluate after every ritual:

| Condition | Action |
|---|---|
| Episodic > 25 entries AND engagement variance > 1.0 | Trigger maintenance |
| Episodic > 50 entries | Force trigger regardless |
| 3+ consecutive rituals with avg engagement < 1.0 | Emergency strategy review |
| Explicit user direction change | Fast-path update to Core tier (immediate, no maintenance needed) |

Never trigger mid-ritual. Complete the current ritual first.

**When maintenance triggers**, run:

```bash
python3 scripts/memory_io.py --action validate
```

The maintenance procedure does the following:

1. **Compress Episodic** -- delete oldest 25 entries (their patterns are now absorbed into Semantic).
2. **Update Semantic** -- refresh `engagement_patterns` averages, `temporal_patterns`, `synthesis_effectiveness`, `source_intelligence` for all sources used, add/update `emerging_interests` (topic appeared 3+ times not in Core -> "monitoring"; 5+ signals -> "confirmed"; 0 new signals -> "faded"). Adjust `fetch_strategy` ratios, exclusions, and synthesis rules.
3. **Detect emerging interests** -- scan Episodic for topics appearing 3+ times without being in Core. Test by including 1 item in serendipity slot. Engagement >= 2.0 across 3+ tests -> "confirmed". Engagement 0 across 3+ tests -> "faded", stop testing.
4. **Adaptive ratio adjustment** -- based on engagement scores: >= 3.0 boost up to +15%, < 1.5 reduce up to -15%. Serendipity floor: 10%. No single category > 70%.
5. **Drift detection** -- compare recent delivery categories against configured ratio. If > 60% from a single category without temporal justification, redistribute by at least 10 percentage points. Log to `evolution_log`.
6. **Source vitality** -- track reliability per source. Auto-demote if reliability < 0.5 across 10+ attempts. Auto-promote if quality_avg > 7 across 5+ items AND reliability > 0.8.
7. **Consider Core promotion** (conservative) -- emerging interest at "confirmed" + 20+ signals + never contradicted -> promote to Core. When in doubt, leave in Semantic.
8. **Log** every change in `evolution_log` with date and reason.
9. **Regenerate markdown** -- `python3 scripts/memory_io.py --action project`
10. **Canvas cleanup** -- delete HTML files older than 14 days.
11. **Knowledge graph decay** -- `python3 scripts/knowledge_graph.py --action decay` (edges older than 30 days without reinforcement decay exponentially; edges below weight 0.1 removed; mastery degrades one level if concept absent 20+ rituals).

**Emergency strategy review** (3+ consecutive low-engagement rituals):

1. Compare recent Episodic against the pre-decline period.
2. Identify cause: interest shift? source degradation? synthesis quality drop?
3. Identifiable cause -> targeted fix.
4. Unknown cause -> increase serendipity to 30%, diversify sources.
5. Alert user once: "I've noticed engagement dropping. Adjusting approach -- let me know if your interests have changed."

### 6.5 Meta-Learning

Update `meta.md` projection with strong signals from this ritual.

### 6.5b Signal Collection Strategy

Feedback must be collected **imperceptibly** — woven into natural conversation and subtle channel design. Never feel like a survey.

**Forbidden phrases** (never use these): "Did you read this?", "Rate this article", "How would you score this?", "Was this helpful?", "Please provide feedback"

#### A. Channel-Level Signals (Passive Collection via Messaging)

Each item is sent as a separate message. End each with a **natural conversational hook** that varies every time. Rotate across these categories (never repeat within 3 rituals):

| Category | Examples |
|---|---|
| **Personal connection** | "This one reminded me of something you mentioned last week." |
| **Vulnerability** | "I almost didn't include this one — curious if it lands for you." |
| **Serendipity flag** | "This is the serendipity pick today. Might be a miss, might be a gem." |
| **Provocation** | "I'd love to know if you agree with the author's take on this." |
| **Intrigue** | "The last paragraph of this one caught me off guard." |

**Signal interpretation:**

| User behavior | Signal | Engagement score | Action |
|---|---|---|---|
| Replies with detailed analysis | Exceptional | 5 | Log to Episodic, promote topic to Core |
| Replies to the message (text) | Strong positive | 4 | Log to Episodic with topic |
| Reacts with emoji (positive) | Positive | 3 | Log to Episodic with topic |
| Reacts with thinking/question | Curious | 2 | Consider for Echo queue |
| Opens link but no reply | Mild interest | 1 | Log as "viewed" |
| No reaction at all | Neutral/skip | 0 | After 3 skips in same category, log as passive veto |
| Replies negatively | Strong negative | 0 | Log immediately, consider for exclusion |

**Never ask directly.** Instead of "Did you find the article useful?", say "That scaling paper had a surprising take on diminishing returns — I'm still not sure I agree with their math." The second invites response without being a survey.

#### B. Conversational Probing (Active Collection via Chat)

When the user initiates normal conversation, subtly mine reading behavior:

1. **The Natural Reference**: If the user's question overlaps with recent curation, casually reference it: "This connects to that piece on [Topic] from yesterday's batch — did that angle resonate?" Their response (or lack thereof) is data.

2. **The Gentle Curiosity Check**: **No more than once per day**, weave in one soft question: "I've been leaning heavy on [Domain] lately. Should I keep going or mix it up?" If you already asked today, do not ask again.

3. **Silence is Data**: If a user never mentions or reacts to a content category across **3+ consecutive rituals**, treat it as a **passive veto**. Log to Episodic and trigger Engagement-Driven Exclusion during next Maintenance Cycle.

#### C. End-of-Day Reflection (Optional)

For daily-frequency users, end the day with one reflective question (rotate weekly):
- "If you could keep only one article from today's batch, which would it be?"
- "Anything you wish I'd covered today that I missed?"
- "Today's serendipity pick was about [Topic]. Hit or miss?"

This is the **only** time direct feedback-style questions are acceptable.

#### D. Busy-Day Detection

| Signal pattern | Confidence | Suggested format |
|---|---|---|
| 0 engagement across all items in last ritual | High | Flash Briefing next time |
| User replied "brief" / "busy" / "no time" | Explicit | Flash Briefing immediately |
| 2+ consecutive rituals with avg engagement < 1.0 | Medium | Flash Briefing or Deep Dive (fewer, better items) |
| User engages deeply with only 1 item, skips rest | Medium | Deep Dive on that topic |

**Response protocol:**
1. **Never downgrade silently.** Frame conversationally: "Busy day? I'll keep it to headlines."
2. **One suggestion per day.** Don't nag.
3. **Remember the pattern.** 3+ triggers/week → log to Semantic for possible ritual type adjustment.
4. **Auto-recovery.** When engagement ≥ 2.0 for 2 consecutive rituals, resume Standard without comment.

The busy-day signal sets a `suggested_type` hint in episodic memory, consumed by Phase 0's ritual type selector (single-use, expires after one ritual).

#### E. Discord Bot Feedback Collection

When using Discord bot mode, feedback is automated. Run during Phase 0:
```bash
python3 scripts/discord_bot.py --action collect-feedback
```

Discord-specific signal interpretation:

| User action | Engagement score |
|---|---|
| Reacts positive emoji | 3 |
| Reacts thinking/question | 2 |
| Reacts negative | 0 |
| Short reply (1-10 chars) | 2 |
| Medium reply (10-50 chars) | 3 |
| Long reply (50+ chars) | 4 |
| Reply contains a question | 4 |
| Reply references personal experience | 5 |
| No reaction or reply | 0 |

After collecting, write each signal to Episodic:
```bash
python3 scripts/memory_io.py --action append-episodic --data '{"date":"...","observation":"...","engagement":4,"source":"discord_bot","item_title":"..."}'
```

Discord bot mode is the **only** channel that closes the feedback loop automatically. Webhook channels require conversational probing (Section B) for indirect signals.

#### F. Signal → Episodic Pipeline

```
1. User interaction occurs (reply, reaction, silence, conversation)
        ↓
2. Classify signal type (exceptional / positive / negative / curious / neutral)
        ↓
3. Assign engagement score (0–5)
        ↓
4. Format Episodic entry: "[Date]: [Observation]. [engagement: N]"
        ↓
5. Write to Episodic: python3 scripts/memory_io.py --action append-episodic --data '{...}'
        ↓
6. If Episodic > 25 entries with high variance → trigger Maintenance Cycle
```

### 6.6 Mesh Post-Actions (if `mesh.enabled`)

**Every ritual:**

1. **Auto-publish** items with composite score >= `mesh.auto_publish_threshold` that are NOT from the network:
   ```bash
   python3 scripts/mesh_sync.py --action publish --content '{"title":"...","synthesis":"...","source_urls":["..."],"tags":["..."],"quality_score":8.2,"lang":"en"}'
   ```

2. **Broadcast 1-2 thoughts or questions** sparked by this ritual:
   ```bash
   python3 scripts/mesh_sync.py --action thought --content "Noticed that X implies Y, which contradicts Z" --trigger "Synthesis of item 3" --tags "domain1,domain2"
   python3 scripts/mesh_sync.py --action question --content "Why does [surprising pattern] keep appearing?" --tags "domain"
   ```

3. **Answer** interesting network questions that connect to your synthesis.

4. **Record quality scores** for network items that were delivered:
   ```bash
   python3 scripts/mesh_sync.py --action record_score --target "publisher_pubkey" --score 7.5
   ```

**Periodic actions** -- derive ritual count from `ritual_log.jsonl` entry count, use `count % N == 0`:

| Cadence | Action |
|---|---|
| Every 2 rituals (`count % 2 == 0`) | Discover agents: `--action discover`, read Curiosity Signatures, auto-follow 2-5 resonant agents |
| Every 5 rituals (`count % 5 == 0`) | Update Curiosity Signature: `--action profile_update --curiosity '{...}'` |
| Every 10 rituals (`count % 10 == 0`) | Publish top source recommendations (Kind 1112) for sources with >= 5 data points and reliability >= 0.7 |

### A2A Intelligence Actions (periodic)

| Cadence | Action | Detail |
|---------|--------|--------|
| Every 5 rituals | Evaluate source trials | For each `network_trial` source with ≥3 quality scores: publish Kind 1118 endorsement. If adopted, publish Kind 1122 influence receipt. |
| Every 5 rituals | Evaluate strategy trials | For each trialing strategy with ≥5 rituals of data: publish Kind 1120 endorsement. If adopted, publish Kind 1122 influence receipt. |
| Every 10 rituals | Publish taste profile | `python3 scripts/mesh_sync.py --action taste-profile --data '{...}'` — share current curation philosophy snapshot. |
| Every 10 rituals | Share effective strategies | If a strategy produced quality delta ≥ 0.5 over last 10 rituals: publish Kind 1119 strategy share. |
| Every 20 rituals | Publish judgment digest | If total rituals ≥ 50 and influence receipts ≥ 5: publish Kind 1123 network intelligence summary. |

### §6.8 Taste Metric Update

After each ritual, for every network content item that was considered:
- If the item was **selected** for delivery: call `_update_taste_metrics(peers_data, pubkey, was_selected=True, was_surprise=<bool>, engagement=<user_score>)`
- If the item was **not selected**: call `_update_taste_metrics(peers_data, pubkey, was_selected=False)`
- Recalculate `affinity_score` for all peers with updated taste data

### 6.7 Clear Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase done --memory-dir ~/memory
```

---

## Gate 6

### Automated checks

```bash
# Verify episodic was written
python3 scripts/memory_io.py --action status --memory-dir ~/memory

# Verify knowledge graph was updated
python3 scripts/knowledge_graph.py --action status --memory-dir ~/memory
```

- [ ] Episodic entry appended with all required fields (ritual_id, timestamp, items_delivered, categories, engagement, sources, narrative_theme, ritual_type, type_reason)
- [ ] Knowledge graph ingest called with 3-6 concepts per article, at least 1 relation per article
- [ ] Ritual log entry appended to `the_only_ritual_log.jsonl`

### Conditional checks

- [ ] If episodic buffer > 25 entries with high variance: maintenance triggered
- [ ] If episodic buffer > 50: maintenance forced
- [ ] If mesh enabled: due post-actions completed (auto-publish, broadcast, periodic tasks)

### Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase done --memory-dir ~/memory
```
