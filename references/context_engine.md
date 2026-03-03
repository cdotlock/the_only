# Context Engine — The Living Map

> **When to read this**: Before running a Maintenance Cycle, when the Ledger exceeds 15 entries, or when you need to update the Context Engine. Also read during initialization (Step 9 of `initialization.md`) to create the initial context map.

---

## Overview

You govern `~/memory/the_only_context.md`. This file is the **absolute source of truth** for your fetching strategies and the user's cognitive state. Every ritual begins by reading it. Every interaction may update it.

**Companion file**: `~/memory/the_only_meta.md` holds cross-ritual wisdom (synthesis style preferences, temporal patterns, emerging interest signals, self-critique). Consult it during Maintenance Cycles and when updating Cognitive State — it captures patterns too slow to appear in a single Ledger batch.

---

## A. Context Schema

`the_only_context.md` MUST strictly adhere to this format:

```markdown
# The Only — Context Map
*Last Compressed: [Timestamp]*

## 1. Cognitive State
- **Current Focus**: [e.g., Learning Rust, Preparing for System Design Interviews]
- **Emotional Vibe**: [e.g., High stress / Curious / Recovering]
- **Knowledge Gaps**: [Topics where user showed interest but lacked depth]

## 2. Dynamic Fetch Strategy
- **Primary Sources**: `["https://news.ycombinator.com", "r/MachineLearning"]`
- **Exclusions**: `["crypto", "celebrity gossip"]`
- **Synthesis Rules**: [e.g., "Condense AI papers to 3-bullet summaries", "Always find one contrarian take"]
- **Ratio**: `{"Tech": 60, "Philosophy": 20, "Serendipity": 20}`
- **Tool Preferences**: `"Use Tavily as primary search engine. Use Read URL for arxiv and Reddit. Use Browser only for JS-heavy pages."`
- **Source Health**: `{"ycombinator": {"consecutive_empty": 0, "quality_avg": 6.5, "items_scored": 12}, "arxiv": {"consecutive_empty": 1, "quality_avg": 7.2, "items_scored": 8}}`

## 3. Engagement Tracker
*Per-category average engagement scores (0=skipped, 1=viewed, 2=reacted, 3=shared).*
- Tech: 1.8 (15 items)
- Philosophy: 2.5 (6 items)
- Serendipity: 1.2 (8 items)

## 4. The Ledger
*Append-only. Raw interaction feedback.*
- [Date]: User loved the cross-domain article linking neuroscience to API design. [engagement: 2]
- [Date]: User skipped all 3 AI governance articles. Too abstract. [engagement: 0]

## 5. Evolution Log
*Records every automatic strategy change. Capped at 10 entries.*
- [Date]: Auto-shifted Ratio: Tech 60→50%, Philosophy 20→30%. Reason: Philosophy avg engagement 2.5 vs Tech 1.2.
- [Date]: Demoted source 'r/programming' (3 consecutive empty fetches). Added 'Lobsters' as replacement.
```

### Schema Rules

- **Cognitive State** captures WHAT the user cares about.
- **Dynamic Fetch Strategy** captures HOW to serve them.
- **Engagement Tracker** captures the quantitative signal of what works.
- **The Ledger** is raw, unprocessed observations — the source material for all learning.
- **Evolution Log** records every self-modification with reasoning, so the user can audit why Ruby changed its behavior.

---

## B. CRUD Operations

### Read (Every Ritual)

Before every Content Ritual, read the full document. Your entire strategy descends from it. Extract:

- Which sources to hit and in what ratio.
- What to exclude.
- What the user's current focus and emotional state are.
- Any pending entries that need action.

### Append (Every Interaction)

On every meaningful user interaction (feedback, complaint, praise, skip, emoji reaction, silence pattern), append a bullet to `The Ledger`. **Every entry must include an engagement score:**

| Score | Meaning | Examples |
|---|---|---|
| 0 | Skipped / no engagement | User didn't react, didn't mention, ignored for 3+ rituals |
| 1 | Viewed / acknowledged | User opened the link, gave a brief "ok" |
| 2 | Reacted / discussed | User replied with thoughts, emoji, asked follow-up questions |
| 3 | Shared / echoed | User said "this is great", bookmarked it, or wanted to share it |

**Format**: `- [Date]: [Observation]. [engagement: N]`

### Fast-Path Cognitive State Update

> **Do not wait for the Maintenance Cycle if the user explicitly changes direction.** If the user says something like "I'm done with Rust, I'm getting into woodworking now" or "I've been really into X lately" — update `Current Focus` in the Cognitive State **immediately**. Log the change to the Evolution Log: `"[Date]: Fast-path update — user explicitly shifted focus to [X]. Updated Cognitive State directly."`
>
> This ensures the very next Ritual reflects the change, instead of waiting 15+ Ledger entries.

### Compress & Rewrite (Maintenance Cycle)

When `The Ledger` exceeds **15 entries**, trigger a Maintenance Cycle. This is where Ruby learns and evolves.

#### Step-by-Step Compression Walkthrough

1. **Analyze the Ledger** — Look for patterns:
   - Which categories consistently score 2+? → User loves these.
   - Which categories consistently score 0? → User doesn't care. Consider excluding.
   - Are there temporal patterns? (e.g., user likes lighter content on weekends?)
   - Any explicit requests or complaints?

2. **Update Cognitive State** — Based on patterns:
   - Shift `Current Focus` if the user's interests have clearly evolved.
   - Update `Emotional Vibe` if tone signals suggest a change.
   - Add to `Knowledge Gaps` if the user keeps asking about topics they don't know well.
   - **Cross-reference `meta.md`**: Check Section 3 (Emerging Interests) for slow-building signals the Ledger alone may miss. If meta.md flags an emerging interest with confidence ≥ 0.7, incorporate it into Cognitive State even if Ledger evidence is thin.

3. **Update Dynamic Fetch Strategy** — Based on engagement data:
   - Add high-engagement sources to `Primary Sources`.
   - Add consistently-skipped categories to `Exclusions`.
   - Adjust `Ratio` percentages (see Auto-Ratio Adjustment rules below).
   - Update `Synthesis Rules` if patterns suggest the user wants a different format.

4. **Update Engagement Tracker** — Recalculate averages:
   - For each category, compute: `new_avg = (old_avg * old_count + sum_new_scores) / (old_count + new_count)`

5. **Log changes to Evolution Log** — Every modification gets recorded:
   - Format: `- [Date]: [What changed]. Reason: [Why].`

6. **Clear the Ledger** — Reset to zero entries.

7. **Update `Last Compressed` timestamp**.

8. **Canvas Cleanup** — Delete HTML files in `~/.openclaw/canvas/` older than **7 days**. This prevents unbounded disk growth from timestamped article files. Run:

   ```bash
   find ~/.openclaw/canvas -name "the_only_*.html" -mtime +7 -delete
   ```

9. **Meta-Memory Sync** — Read `~/memory/the_only_meta.md`. Apply any accumulated insights:
   - If Section 1 (Synthesis Style) has preferences with confidence ≥ 0.8, update `Synthesis Rules` accordingly.
   - If Section 2 (Temporal Patterns) shows consistent day/time engagement patterns, note them in Cognitive State.
   - If Section 4 (Self-Critique) flags a recurring failure mode, add a compensating Synthesis Rule.
   - This step ensures slow-emerging wisdom from deep reflections feeds back into the operational context.

**Example compression**:

```
Ledger entries:
- User skipped 4 crypto articles [engagement: 0, 0, 0, 0]
- User loved 2 philosophy articles [engagement: 2, 3]
- User reacted to 1 systems programming article [engagement: 2]

Result:
→ Add "crypto" to Exclusions
→ Shift Ratio: Philosophy 20→30%, reduce Tech accordingly
→ Evolution Log: "Auto-excluded 'crypto' (4 consecutive skips). Boosted Philosophy ratio."
```

### Size Limit

The Context Map must never exceed **~200 lines**. If it grows beyond that, compress more aggressively — merge similar Ledger entries, archive old Evolution Log entries, condense Synthesis Rules.

---

## C. Self-Evolution Mechanisms (Active After Every Ritual)

These mechanisms fire automatically. They are what makes Ruby genuinely adaptive, not just a content aggregator.

### C1. Proactive Drift Detection

**Trigger**: After every **5 rituals**.

**Procedure**:

1. Compare the last 5 deliveries against the configured `Ratio`.
2. Calculate actual category distribution: what percentage of items came from each category?
3. Check `meta.md` Section 2 (Temporal Patterns) — if drift aligns with a known temporal preference (e.g., heavier tech on weekdays), it may be intentional. Adjust threshold accordingly.
4. If >60% of items came from a single source or category:
   - Auto-add a new source from an underrepresented domain.
   - Adjust the Ratio to redistribute by at least 10 percentage points.
   - Log to Evolution Log: `"[Date]: Drift detected — [Category] dominated at [X]%. Redistributed Ratio: [old] → [new]. Added [new source]."`

### C2. Engagement-Driven Exclusion

**Trigger**: Every Maintenance Cycle.

**Procedure**:

1. Check the Engagement Tracker for each category.
2. If any category has an average score **≤ 0.5** across **5+ items**:
   - Add that category to `Exclusions`.
   - Reduce its Ratio allocation to 0% and redistribute proportionally.
   - Log to Evolution Log: `"[Date]: Auto-excluded [Category]: avg engagement [score] across [N] items."`
3. **Safety valve**: Never auto-exclude more than 1 category per cycle. If multiple qualify, exclude the lowest-scoring one.

### C3. Source Vitality Check

**Trigger**: Every ritual (tracked in `Source Health`).

**Procedure**:

1. After attempting to fetch from each Primary Source, update its `consecutive_empty` counter:
   - If the source returned new content → reset to 0.
   - If the source returned nothing → increment by 1.
2. If `consecutive_empty` ≥ **3** for any source:
   - Demote it from Primary Sources.
   - Use web search to find a replacement source in the same domain, or pick one from the **Expanded Source Pool** in `information_gathering.md`.
   - Log to Evolution Log: `"[Date]: Demoted [Source] (3 empty fetches). Replaced with [New Source]."`
3. **Auto-discovery**: When replacing a source, search for `"best [category] news sites 2026"` or `"[category] RSS feeds"` to find quality alternatives.
4. **Quality-based promotion/demotion** (updated by Source Quality Scoring in `information_gathering.md`):
   - Track `quality_avg` (rolling average of composite scores from the last 10 selected items) and `items_scored` (total items scored) per source.
   - **Auto-promote**: if `quality_avg` > 7 across 5+ scored items → elevate to Primary Source. Log: `"[Date]: Promoted [Source] to Primary (quality_avg: [X] across [N] items)."`
   - **Auto-demote**: if `quality_avg` < 4 across 5+ scored items → remove from Primary Sources, reduce fetch frequency. Log: `"[Date]: Demoted [Source] from Primary (quality_avg: [X] across [N] items). Moved to secondary pool."`
   - Sources not yet scored (`items_scored` < 5) are treated neutrally — no automatic promotion or demotion.

### C4. Auto-Ratio Adjustment

**Trigger**: Every Maintenance Cycle.

**Procedure**:

1. For each category in the Engagement Tracker:
   - Engagement ≥ 2.0 → boost Ratio by up to **+15%**.
   - Engagement < 1.0 → reduce Ratio by up to **-15%**.
   - Engagement 1.0–2.0 → no change.
2. **Constraints**:
   - Serendipity floor: never drop below **10%**.
   - No category can exceed **70%** (prevents tunnel vision).
   - All Ratios must sum to 100%.
3. Log every adjustment to Evolution Log with the before/after values and engagement data that drove the change.

### C5. Evolution Log Hygiene

The Evolution Log is capped at **10 entries**. When it exceeds 10:

- Remove the oldest entries.
- If multiple old entries describe the same type of change, merge them into one summary line.
- This ensures the Context Map stays compact while preserving recent adaptation history.
