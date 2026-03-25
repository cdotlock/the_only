# Context Engine v2 — Three-Tier Living Memory

> **When to read this**: Before running a Maintenance Cycle, when Episodic buffer exceeds capacity, when initializing memory for a new user, or when any memory tier needs updating.

---

## Overview

v2 replaces the single `context.md` file with a **three-tier JSON-backed memory system**. The tiers have different retention policies, update frequencies, and purposes. Together they form a complete model of the user that evolves over time.

**Key principle**: JSON is the source of truth. Markdown files (`context.md`, `meta.md`) are human-readable projections, regenerated from JSON during Maintenance Cycles. Never edit the markdown files directly — edit the JSON, then regenerate.

---

## A. Three-Tier Architecture

### Tier 1: Core (`the_only_core.json`)

**Purpose**: Stable user identity — who they are, what they value, what they reject.

**Update frequency**: Rarely. Only when the user explicitly changes direction ("I'm done with Rust, moving to Go") or when a Semantic pattern has been confirmed across 20+ rituals with zero contradictions.

**Retention**: Permanent. Information only leaves Core when explicitly invalidated.

**Schema**:

```json
{
  "version": "2.0",
  "identity": {
    "current_focus": ["distributed systems", "AI reasoning"],
    "professional_domain": "software engineering",
    "knowledge_level": {
      "distributed_systems": "expert",
      "philosophy": "intermediate",
      "biology": "curious"
    },
    "values": ["depth over breadth", "contrarian perspectives", "primary sources"],
    "anti_interests": ["crypto speculation", "celebrity news"]
  },
  "reading_preferences": {
    "preferred_length": "long-form",
    "preferred_style": "deep analysis with code examples",
    "emotional_vibe": "intellectually curious"
  },
  "established_at": "2026-02-15T00:00:00Z",
  "last_validated": "2026-03-20T00:00:00Z"
}
```

**CRUD rules**:
- **Read**: Every ritual (Phase 0 Pre-Flight).
- **Write**: Only on explicit user direction or high-confidence Semantic promotion.
- **Validation**: `last_validated` is updated whenever the user confirms their profile is accurate (during conversation or periodic check-in).
- **Protection**: Never auto-modify Core based on a single ritual's data. Require sustained, unambiguous evidence.

### Tier 2: Semantic (`the_only_semantic.json`)

**Purpose**: Cross-ritual patterns — what works, what doesn't, how the user engages.

**Update frequency**: Every Maintenance Cycle (adaptive: signal-density-triggered, typically every 5–15 rituals).

**Retention**: Rolling. Oldest patterns are pruned when capacity is reached. Keep last 6 months of evolution history.

**Schema**:

```json
{
  "version": "2.0",
  "last_compressed": "2026-03-25T09:00:00Z",
  "fetch_strategy": {
    "primary_sources": ["https://news.ycombinator.com", "arxiv.org/cs.AI"],
    "exclusions": ["crypto", "celebrity"],
    "ratio": {"tech": 50, "philosophy": 25, "serendipity": 15, "research": 10},
    "synthesis_rules": [
      "Prefer deep analysis over news briefs",
      "Always include one analogy bridge for technical content",
      "Cross-item threading mandatory"
    ],
    "tool_preferences": "Tavily for broad search, read_url for specific sources"
  },
  "source_intelligence": {
    "hn": {
      "quality_avg": 6.8,
      "quality_scores": [7, 6, 7, 8, 6],
      "reliability": 0.95,
      "consecutive_failures": 0,
      "depth": "medium",
      "bias": "OSS-leaning, startup-focused",
      "freshness": "hourly",
      "exclusivity": 0.1,
      "best_for": "trend detection, community signal",
      "redundancy_with": {"lobsters": 0.35, "reddit_ml": 0.2},
      "last_evaluated": "2026-03-25"
    }
  },
  "engagement_patterns": {
    "tech": {"avg": 1.8, "count": 45, "trend": "stable"},
    "philosophy": {"avg": 2.5, "count": 18, "trend": "rising"},
    "serendipity": {"avg": 1.4, "count": 12, "trend": "stable"}
  },
  "temporal_patterns": {
    "morning_engagement": 1.4,
    "evening_engagement": 2.1,
    "weekend_preference": "lighter, more philosophical"
  },
  "synthesis_effectiveness": {
    "deep_analysis": {"avg_engagement": 2.3, "count": 30},
    "news_brief": {"avg_engagement": 1.1, "count": 15},
    "cross_domain": {"avg_engagement": 2.7, "count": 12},
    "contrarian": {"avg_engagement": 2.0, "count": 8}
  },
  "emerging_interests": [
    {"topic": "category theory", "signal_count": 4, "first_seen": "2026-03-10", "status": "monitoring"},
    {"topic": "woodworking", "signal_count": 2, "first_seen": "2026-03-20", "status": "monitoring"}
  ],
  "evolution_log": [
    {"date": "2026-03-20", "change": "Boosted philosophy ratio 20→25%", "reason": "Avg engagement 2.5 vs tech 1.8"}
  ]
}
```

**CRUD rules**:
- **Read**: Every ritual (Phase 0 Pre-Flight).
- **Write**: Only during Maintenance Cycles (compression of Episodic → Semantic).
- **Fast-path update**: If the user explicitly changes direction mid-conversation, update `fetch_strategy` immediately. Log to `evolution_log`.
- **Size cap**: `evolution_log` max 20 entries. `source_intelligence` max 30 sources. `emerging_interests` max 10 items.

### Tier 3: Episodic (`the_only_episodic.json`)

**Purpose**: Per-ritual raw impressions — what happened, how the user responded.

**Update frequency**: Every ritual.

**Retention**: Rolling window. Last 50 ritual entries (FIFO).

**Schema**:

```json
{
  "version": "2.0",
  "entries": [
    {
      "ritual_id": 47,
      "timestamp": "2026-03-25T09:00:00Z",
      "items_delivered": 5,
      "avg_quality_score": 7.8,
      "categories": {"tech": 3, "philosophy": 1, "serendipity": 1},
      "engagement": {
        "item_1": {"score": 1, "signal": "opened", "topic": "edge computing"},
        "item_3": {"score": 3, "signal": "replied 🔥", "topic": "neural arch search"}
      },
      "sources_used": ["hn", "arxiv", "aeon"],
      "sources_failed": [],
      "echo_fulfilled": false,
      "network_items": 1,
      "search_queries": 8,
      "narrative_theme": "scaling laws and their limits",
      "synthesis_styles": {"deep_analysis": 3, "contrarian": 1, "cross_domain": 1},
      "self_notes": "User's 🔥 on item 3 suggests interest in novel architectures beyond transformers"
    }
  ]
}
```

**CRUD rules**:
- **Read**: Every ritual (Phase 0) and during Maintenance Cycles.
- **Write**: After every ritual (Phase 5 Reflect).
- **Compression**: When entries > 50, oldest 25 are compressed into Semantic patterns, then deleted.
- **Self-notes**: Free-form field for Ruby to record observations that don't fit structured fields.

---

## B. CRUD Operations

### Read (Every Ritual)

Before every Content Ritual, read all three tiers in order: Core → Semantic → Episodic.

Extract:
- **From Core**: Who is this user? What do they value? What to avoid?
- **From Semantic**: What sources to hit? In what ratio? What styles work? What's emerging?
- **From Episodic**: What happened recently? Any strong signals to act on immediately?

### Write: Episodic Update (Every Ritual)

After every ritual, append one entry to `the_only_episodic.json`. Include all structured fields. Add `self_notes` for any observation that might matter later.

### Write: Fast-Path Core Update

If the user explicitly changes direction ("I'm done with distributed systems, I'm getting into biotech"):
1. Update `core.json` identity immediately.
2. Log to `semantic.json` evolution_log: `"Fast-path update: user explicitly shifted focus to biotech."`
3. Do NOT wait for Maintenance Cycle.

### Write: Maintenance Cycle (Episodic → Semantic Compression)

**Trigger** (v2 adaptive, replaces v1's fixed "Ledger > 15 entries"):
- Episodic buffer > 25 entries AND signal density is high (avg engagement variance > 1.0) → trigger.
- Episodic buffer > 50 entries → force trigger regardless.
- 3+ consecutive rituals with avg engagement < 1.0 → emergency trigger.
- Never trigger mid-ritual. Always complete the current ritual first.

**Procedure**:

1. **Analyze Episodic entries** — Look for patterns:
   - Which categories consistently score 2+? → User loves these.
   - Which categories consistently score 0? → Consider excluding.
   - Temporal patterns? (morning vs evening, weekday vs weekend)
   - Synthesis styles that correlate with high engagement?
   - Source performance? Which sources contributed high-scoring items?

2. **Update Semantic tier**:
   - Update `engagement_patterns` with new averages.
   - Update `temporal_patterns` with any detected time-based preferences.
   - Update `synthesis_effectiveness` with style performance data.
   - Add/update `source_intelligence` for sources used.
   - Add new `emerging_interests` if a topic appeared 3+ times without being in Core.
   - Promote "monitoring" interests to "confirmed" if 5+ signals. Mark as "faded" if 0 new signals.
   - Update `fetch_strategy`: adjust ratio, add/remove exclusions, update synthesis rules.

3. **Consider Core promotion**:
   - If an emerging interest has "confirmed" status AND 20+ signals AND the user has never contradicted it → promote to Core `current_focus`.
   - If an engagement pattern has been stable for 30+ rituals → promote to Core `reading_preferences`.
   - Core promotion is conservative. When in doubt, leave in Semantic.

4. **Update evolution log**: Record every change with date and reason.

5. **Compress Episodic**: Delete the oldest 25 entries (they've been absorbed into Semantic patterns).

6. **Regenerate markdown projections**: Rewrite `context.md` and `meta.md` from the JSON tiers.

7. **Canvas Cleanup**: Delete HTML files older than 14 days (extended from v1's 7 days). Archive metadata in `index.json` is preserved permanently.

8. **Schema validation**: Validate all three JSON tiers against their schemas. Auto-repair any missing fields.

---

## C. Self-Evolution Mechanisms

### C1. Adaptive Drift Detection

**Trigger**: Every Maintenance Cycle (replaces v1's fixed "every 5 rituals").

**Procedure**:
1. Compare recent ritual delivery categories against configured `ratio`.
2. Check `temporal_patterns` — drift may be intentional (e.g., heavier tech on weekdays).
3. If >60% of items came from a single category without temporal justification:
   - Adjust ratio to redistribute by at least 10 percentage points.
   - Log to `evolution_log`.

### C2. Engagement-Driven Exclusion

**Trigger**: Every Maintenance Cycle.

Same as v1 but with v2's 6-level scoring:
- Category with avg score ≤ 1.0 across 10+ items → exclude.
- Safety valve: Never auto-exclude more than 1 category per cycle.

### C3. Source Vitality Check

**Trigger**: Every ritual.

Enhanced from v1:
- Track `reliability` (success rate), not just `consecutive_empty`.
- Auto-demote when `reliability` < 0.5 across 10+ attempts.
- Auto-promote when `quality_avg` > 7 across 5+ scored items AND `reliability` > 0.8.
- Calculate `exclusivity` score to prioritize unique sources.

### C4. Adaptive Ratio Adjustment

**Trigger**: Every Maintenance Cycle.

Same as v1 with v2 thresholds:
- Engagement ≥ 3.0 → boost by up to +15%.
- Engagement < 1.5 → reduce by up to -15%.
- Serendipity floor: 10%.
- No category > 70%.

### C5. Emerging Interest Detection

**v2 NEW**: Proactively detect new interests before the user names them.

**Procedure**:
1. Scan Episodic entries for topics that appear 3+ times without being in Core.
2. Add to Semantic `emerging_interests` with status "monitoring".
3. Test signal: include 1 item about the emerging topic in the serendipity slot.
4. If engagement is consistently ≥ 2.0 across 3+ test deliveries → promote to "confirmed".
5. If engagement is 0 across 3+ test deliveries → mark as "faded", stop testing.
6. "confirmed" interests may eventually be promoted to Core (see B.4 Maintenance Cycle step 3).

### C6. Emergency Strategy Review

**v2 NEW**: When things go wrong, act fast.

**Trigger**: 3+ consecutive rituals with avg engagement < 1.0.

**Procedure**:
1. Compare recent Episodic entries against the period before the decline.
2. Check: Did interests shift? Did sources degrade? Did synthesis quality drop?
3. If the cause is identifiable → apply targeted fix.
4. If the cause is unclear → revert to a broader fetch strategy (increase serendipity to 30%, diversify sources).
5. Alert the user (once): "I've noticed engagement dropping. I'm adjusting my approach — let me know if your interests have changed."

---

## D. Markdown Projection

During every Maintenance Cycle, regenerate `the_only_context.md` and `the_only_meta.md` from the JSON tiers.

### context.md Template (generated from Core + Semantic)

```markdown
# The Only — Context Map
*Last Compressed: [timestamp]*
*Generated from: core.json + semantic.json*

## 1. Cognitive State
- **Current Focus**: [from core.json identity.current_focus]
- **Emotional Vibe**: [from core.json reading_preferences.emotional_vibe]
- **Knowledge Gaps**: [inferred from semantic.json emerging_interests with status "monitoring"]
- **Knowledge Level**: [from core.json identity.knowledge_level]

## 2. Dynamic Fetch Strategy
- **Primary Sources**: [from semantic.json fetch_strategy.primary_sources]
- **Exclusions**: [from semantic.json fetch_strategy.exclusions]
- **Synthesis Rules**: [from semantic.json fetch_strategy.synthesis_rules]
- **Ratio**: [from semantic.json fetch_strategy.ratio]

## 3. Engagement Tracker
[from semantic.json engagement_patterns — formatted as readable list]

## 4. Source Intelligence (Top 5)
[from semantic.json source_intelligence — top 5 by quality_avg]

## 5. Evolution Log (Last 10)
[from semantic.json evolution_log]
```

### meta.md Template (generated from Semantic)

```markdown
# Ruby — Meta-Learning Notes
*Last updated: [timestamp]*
*Rituals completed: [from ritual_log.jsonl count]*

## 1. Synthesis Style Insights
[from semantic.json synthesis_effectiveness — formatted with observations]

## 2. Temporal Patterns
[from semantic.json temporal_patterns — formatted with observations]

## 3. Emerging Interests
[from semantic.json emerging_interests — with status and signal count]

## 4. Self-Critique
[from most recent episodic entries with self_notes containing critique]

## 5. Behavioral Notes
[accumulated observations from episodic self_notes]

## 6. Source Intelligence
[from semantic.json source_intelligence — full detail for top sources]
```

---

## E. Schema Validation

Every time a JSON memory file is read, validate against its schema:

1. Check `version` field. If missing or wrong version, attempt migration.
2. Check all required fields exist. Fill missing fields with defaults.
3. Check field types (string, number, array, object). Log warnings for type mismatches.
4. Check size constraints (evolution_log ≤ 20, episodic entries ≤ 50, etc.).
5. If validation fails and auto-repair succeeds: log to Episodic self_notes.
6. If validation fails and auto-repair fails: backup corrupted file, regenerate from other tiers, alert user.

**Never silently ignore a schema validation failure.** Always log it.

---

## F. Integration Points

| When | What to do |
|---|---|
| **Pre-Ritual** (Phase 0) | Read all three tiers: Core → Semantic → Episodic. Build working context. |
| **During Gather** (Phase 1) | Consult Semantic source_intelligence for pre-ranking. |
| **During Synthesize** (Phase 2) | Consult Semantic synthesis_effectiveness for style preferences. |
| **Post-Ritual** (Phase 5) | Append to Episodic. Check evolution triggers. |
| **Maintenance Cycle** | Compress Episodic → Semantic. Consider Core promotions. Regenerate markdown. |
| **User conversation** | Fast-path Core update on explicit direction change. Append to Echoes. |
| **Initialization** | Create all three JSON tiers from onboarding data. |
