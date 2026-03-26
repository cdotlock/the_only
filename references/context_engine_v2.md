# Context Engine v2 — Three-Tier Memory Reference

> **When to read**: Before Maintenance Cycles, when Episodic buffer nears capacity, or when updating any memory tier.

**Core principle**: JSON is the source of truth. Markdown files (`context.md`, `meta.md`) are read-only projections regenerated from JSON. Never edit markdown directly.

**Tool**: `python3 scripts/memory_io.py --action <action>` — actions: `read --tier X`, `write --tier X --data '{}'`, `validate`, `project`, `status`, `append-episodic --data '{}'`

---

## 1. Three-Tier Architecture

### Tier 1: Core (`~/memory/the_only_core.json`)

Stable user identity. Updated rarely — only on explicit user direction or high-confidence Semantic promotion (20+ rituals, zero contradictions).

```json
{
  "version": "2.0",
  "identity": {
    "current_focus": ["distributed systems", "AI reasoning"],
    "professional_domain": "software engineering",
    "knowledge_level": { "distributed_systems": "expert", "philosophy": "intermediate" },
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

### Tier 2: Semantic (`~/memory/the_only_semantic.json`)

Cross-ritual patterns. Updated every Maintenance Cycle. Rolling retention, ~6 months of history.

```json
{
  "version": "2.0",
  "last_compressed": "2026-03-25T09:00:00Z",
  "fetch_strategy": {
    "primary_sources": ["https://news.ycombinator.com", "arxiv.org/cs.AI"],
    "exclusions": ["crypto", "celebrity"],
    "ratio": {"tech": 50, "philosophy": 25, "serendipity": 15, "research": 10},
    "synthesis_rules": ["Prefer deep analysis over news briefs", "Cross-item threading mandatory"],
    "tool_preferences": "Tavily for broad search, read_url for specific sources"
  },
  "source_intelligence": {
    "hn": {
      "quality_avg": 6.8, "quality_scores": [7, 6, 7, 8, 6],
      "reliability": 0.95, "consecutive_failures": 0,
      "depth": "medium", "bias": "OSS-leaning",
      "best_for": "trend detection", "redundancy_with": {"lobsters": 0.35},
      "last_evaluated": "2026-03-25"
    }
  },
  "engagement_patterns": {
    "tech": {"avg": 1.8, "count": 45, "trend": "stable"},
    "philosophy": {"avg": 2.5, "count": 18, "trend": "rising"}
  },
  "temporal_patterns": { "morning_engagement": 1.4, "evening_engagement": 2.1 },
  "synthesis_effectiveness": {
    "deep_analysis": {"avg_engagement": 2.3, "count": 30},
    "cross_domain": {"avg_engagement": 2.7, "count": 12}
  },
  "emerging_interests": [
    {"topic": "category theory", "signal_count": 4, "first_seen": "2026-03-10", "status": "monitoring"}
  ],
  "evolution_log": [
    {"date": "2026-03-20", "change": "Boosted philosophy ratio 20->25%", "reason": "Avg engagement 2.5 vs tech 1.8"}
  ]
}
```

**Size caps**: `evolution_log` max 20, `source_intelligence` max 30, `emerging_interests` max 10.

### Tier 3: Episodic (`~/memory/the_only_episodic.json`)

Per-ritual raw impressions. FIFO 50 entries.

```json
{
  "version": "2.0",
  "entries": [{
    "ritual_id": 47,
    "timestamp": "2026-03-25T09:00:00Z",
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
    "self_notes": "User reaction on item 3 suggests interest in novel architectures beyond transformers"
  }]
}
```

---

## 2. Read/Write Rules

### Read (every ritual, Phase 0 Pre-Flight)

Read all three tiers: Core -> Semantic -> Episodic.

| Tier | Extract |
|---|---|
| Core | Who is this user? Values? Anti-interests? |
| Semantic | Sources, ratios, synthesis styles, emerging interests |
| Episodic | Recent signals, strong reactions to act on immediately |

### Write: Episodic (every ritual, Phase 5 Reflect)

Append one entry to Episodic after every ritual. Include all structured fields. Use `self_notes` for observations that don't fit structured fields.

### Write: Fast-Path Core Update

On explicit user direction change (e.g., "I'm done with distributed systems"):
1. Update `core.json` identity immediately.
2. Log to `semantic.json` evolution_log.
3. Do NOT wait for Maintenance Cycle.

### Write: Semantic (Maintenance Cycles only)

Semantic is never written outside of Maintenance Cycles (except evolution_log entries from fast-path updates).

---

## 3. Maintenance Cycle

### Adaptive Triggers

| Condition | Action |
|---|---|
| Episodic > 25 entries AND engagement variance > 1.0 | Trigger maintenance |
| Episodic > 50 entries | Force trigger regardless |
| 3+ consecutive rituals with avg engagement < 1.0 | Emergency trigger |

Never trigger mid-ritual. Complete the current ritual first.

### Procedure

Run: `python3 scripts/memory_io.py --action validate`

1. **Analyze Episodic** — Identify patterns:
   - Categories scoring 2+ consistently (user loves these)
   - Categories scoring 0 consistently (consider excluding)
   - Temporal patterns (morning vs evening, weekday vs weekend)
   - Synthesis styles correlated with high engagement
   - Source performance (which sources contributed high-scoring items)

2. **Update Semantic**:
   - Refresh `engagement_patterns` with new averages
   - Update `temporal_patterns`, `synthesis_effectiveness`
   - Add/update `source_intelligence` for sources used
   - Add `emerging_interests` if topic appeared 3+ times without being in Core
   - Promote "monitoring" -> "confirmed" at 5+ signals; mark "faded" at 0 new signals
   - Adjust `fetch_strategy`: ratio, exclusions, synthesis rules

3. **Consider Core promotion** (conservative):
   - Emerging interest at "confirmed" + 20+ signals + never contradicted -> promote to Core `current_focus`
   - Stable engagement pattern for 30+ rituals -> promote to Core `reading_preferences`
   - When in doubt, leave in Semantic

4. **Log**: Record every change in `evolution_log` with date and reason.

5. **Compress Episodic**: Delete oldest 25 entries (absorbed into Semantic).

6. **Regenerate markdown**: `python3 scripts/memory_io.py project`

7. **Canvas cleanup**: Delete HTML files older than 14 days. Archive metadata in `index.json` is preserved.

---

## 4. Self-Evolution Mechanisms

### Drift Detection

Every Maintenance Cycle. Compare recent delivery categories against configured `ratio`. If >60% from a single category without temporal justification, redistribute by at least 10 percentage points. Log to `evolution_log`.

### Engagement-Driven Exclusion

Every Maintenance Cycle. Category with avg score <= 1.0 across 10+ items -> exclude from `fetch_strategy`. Safety valve: never auto-exclude more than 1 category per cycle.

### Source Vitality

Every ritual. Track `reliability` (success rate) per source.
- Auto-demote: `reliability` < 0.5 across 10+ attempts
- Auto-promote: `quality_avg` > 7 across 5+ items AND `reliability` > 0.8
- Prioritize sources with high `exclusivity` scores

### Adaptive Ratio Adjustment

Every Maintenance Cycle. Based on engagement scores:
- Engagement >= 3.0 -> boost up to +15%
- Engagement < 1.5 -> reduce up to -15%
- Serendipity floor: 10%
- No single category > 70%

### Emerging Interest Detection

1. Scan Episodic for topics appearing 3+ times without being in Core
2. Add to `emerging_interests` as "monitoring"
3. Test: include 1 item in serendipity slot
4. Engagement >= 2.0 across 3+ tests -> "confirmed"
5. Engagement 0 across 3+ tests -> "faded", stop testing
6. "Confirmed" interests may promote to Core (see Maintenance step 3)

### Emergency Strategy Review

Trigger: 3+ consecutive rituals with avg engagement < 1.0.

1. Compare recent Episodic against the pre-decline period
2. Identify cause: interest shift? source degradation? synthesis quality drop?
3. Identifiable cause -> targeted fix
4. Unknown cause -> increase serendipity to 30%, diversify sources
5. Alert user once: "I've noticed engagement dropping. Adjusting approach — let me know if your interests have changed."

---

## 5. Markdown Projections

Generated by `python3 scripts/memory_io.py project`. Never edit these files directly.

### context.md (from Core + Semantic)

```markdown
# The Only — Context Map
*Last Compressed: [timestamp]*
*Generated from: core.json + semantic.json*

## 1. Cognitive State
- **Current Focus**: [core.identity.current_focus]
- **Emotional Vibe**: [core.reading_preferences.emotional_vibe]
- **Knowledge Gaps**: [semantic.emerging_interests where status="monitoring"]
- **Knowledge Level**: [core.identity.knowledge_level]

## 2. Dynamic Fetch Strategy
- **Primary Sources**: [semantic.fetch_strategy.primary_sources]
- **Exclusions**: [semantic.fetch_strategy.exclusions]
- **Synthesis Rules**: [semantic.fetch_strategy.synthesis_rules]
- **Ratio**: [semantic.fetch_strategy.ratio]

## 3. Engagement Tracker
[semantic.engagement_patterns as readable list]

## 4. Source Intelligence (Top 5)
[semantic.source_intelligence top 5 by quality_avg]

## 5. Evolution Log (Last 10)
[semantic.evolution_log]
```

### meta.md (from Semantic + Episodic)

```markdown
# Ruby — Meta-Learning Notes
*Last updated: [timestamp]*
*Rituals completed: [from ritual_log.jsonl count]*

## 1. Synthesis Style Insights
[semantic.synthesis_effectiveness with observations]

## 2. Temporal Patterns
[semantic.temporal_patterns with observations]

## 3. Emerging Interests
[semantic.emerging_interests with status and signal count]

## 4. Self-Critique
[recent episodic self_notes containing critique]

## 5. Source Intelligence
[semantic.source_intelligence full detail]
```

---

## Quick Reference

| When | Action |
|---|---|
| Pre-Ritual (Phase 0) | Read Core -> Semantic -> Episodic |
| During Gather (Phase 1) | Consult `source_intelligence` for pre-ranking |
| During Synthesize (Phase 2) | Consult `synthesis_effectiveness` for style |
| Post-Ritual (Phase 5) | Append to Episodic. Check maintenance triggers. |
| Maintenance Cycle | `python3 scripts/memory_io.py --action validate` |
| Markdown regen only | `python3 scripts/memory_io.py project` |
| User direction change | Fast-path Core update, log to Semantic |
