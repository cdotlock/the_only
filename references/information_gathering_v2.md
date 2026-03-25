# Information Gathering v2 — Adaptive Depth-First Strategy

> **When to read this**: At the start of every Content Ritual, before gathering any information. This document governs how you find, fetch, evaluate, and select content in v2.

> **⛔ STOP**: Before reading this document, confirm you have completed **Pre-Flight** (SKILL_v2.md Phase 0). You MUST have read all three memory tiers before proceeding. If you have not, go back now.

**Contents**: Philosophy Change · Pre-Check · Phase 0: Search Thesis · Source Pre-Ranking · Adaptive Search · Six Layers · Depth-First Candidate Evaluation · Quality Scoring (6 Dimensions) · Graph-Level Modifiers · Narrative Arc Construction · Graceful Degradation · Expanded Source Pool · Source Intelligence Protocol

---

## Philosophy Change: v1 → v2

| v1 | v2 |
|----|-----|
| Scan 100+ items, score by metadata | Deeply evaluate 20–30 items, score by actual content |
| Fixed 3-round search (breadth→depth→contrarian) | Adaptive search that follows promising threads |
| All sources fetched equally | Source pre-ranking — skip low-yield sources |
| Independent per-item scoring | Graph-level analysis: tension, redundancy, cross-domain |
| Items delivered as a list | Items arranged in a narrative arc |

**The core insight**: A ritual of 5 deeply understood articles beats a ritual of 5 well-headlined articles every time. The quality bottleneck in v1 was comprehension, not discovery.

---

## Pre-Check: Runtime Tool Detection

Same as v1 — check `capabilities` from config, verify search tools, handle fallbacks.

**v2 addition**: Also check Source Intelligence in `the_only_semantic.json` for tool-specific performance data. If a tool's reliability has dropped below 0.5, warn and consider alternatives.

---

## Phase 0: Search Thesis (Think Before You Search)

Based on all three memory tiers + ritual log, answer these 5 questions silently:

1. **What does the user care about right now?** — From `core.json` identity + `semantic.json` engagement patterns.
2. **What's happening in the world that might affect them?** — Date, trends, recent events in their domains.
3. **What angle would they NOT think of themselves?** — Cross-domain connection, contrarian take, historical parallel.
4. **What did I give them last time?** — Check `ritual_log.jsonl` last 3 entries. Avoid repeating categories/sources/angles across consecutive rituals.
5. **What deserves a counterargument?** — If the user's focus has a dominant narrative, actively seek dissent.

**v2 addition**:
6. **What narrative could connect today's items?** — Before searching, hypothesize a possible ritual theme. This doesn't constrain search but provides a lens for evaluation. Example: "The tension between automation and craft" could thread through AI scaling, artisan manufacturing, and a philosophy piece on human skill.

---

## Source Pre-Ranking

**v2 NEW**: Before fetching anything, rank sources by expected yield.

### Procedure

1. Read `source_intelligence` from `the_only_semantic.json`.
2. For each Primary Source, calculate:

```
expected_yield(source) = quality_avg × reliability × freshness_factor × (1 - redundancy_with_fetched)
```

Where:
- `quality_avg`: rolling average of composite scores from items selected from this source (0–10)
- `reliability`: fraction of recent fetches that returned content (0–1)
- `freshness_factor`: 1.0 if updated within fetch window, 0.5 if stale, 0.0 if unknown
- `redundancy_with_fetched`: fraction of this source's recent output that overlaps with already-fetched sources (0–1)

3. Rank sources by `expected_yield` descending.
4. **Skip threshold**: Sources with `expected_yield < 2.0` are skipped for this ritual. They're not deleted — they'll be re-evaluated next time.
5. **Mandatory inclusion**: At least 3 source categories must be represented (aggregator, blog, paper, serendipity). If pre-ranking would eliminate a whole category, force-include the best source from that category.

### Why This Matters

v1 fetched all primary sources equally — a source with reliability 0.3 got the same time as one with reliability 0.95. Pre-ranking ensures the ritual spends time on the sources most likely to yield valuable candidates, reducing total gathering time by 30–50%.

---

## Adaptive Search Strategy

**v2 REPLACES the fixed 3-round search from v1.**

### How It Works

Instead of fixed rounds (breadth → depth → contrarian), v2 uses a thread-following approach:

```
START: Generate 3–4 broad queries from Search Thesis
  │
  ├─ Query 1 → Results → Scan for promising threads
  ├─ Query 2 → Results → Scan for promising threads  
  ├─ Query 3 → Results → Scan for promising threads
  │
  ▼
EVALUATE: Which thread is most promising?
  │
  ├─ Thread A (most interesting) → 2–3 depth queries
  │   ├─ Find primary source
  │   ├─ Find author's other work  
  │   └─ Find opposing viewpoint
  │
  ├─ Thread B (second) → 1–2 depth queries
  │
  ▼
CHECK: Is a dominant narrative emerging?
  │
  ├─ Yes → 1–2 contrarian queries to challenge it
  └─ No  → 1 more broad query to find unexpected angles
  │
  ▼
DONE: 6–10 total searches, each with clear purpose
```

### Key Differences from v1

1. **No mandatory minimums**: If 6 searches yield excellent candidates, stop. Don't search to fill a quota.
2. **Thread-following**: When a search reveals something promising, follow it deeper instead of moving to the next prescribed round.
3. **Contrarian is conditional**: Only probe contrarian angles when a dominant narrative has emerged. If the results are already diverse, skip it.
4. **Quality over quantity**: Each search should be crafted based on what you've already found, not generated from a template.

---

## Six Layers of Information

### Layer 1: Real-Time Pulse

Same sources and fallback chain as v1. One key change:

**v2**: After fetching from pre-ranked sources, evaluate headlines against the Search Thesis. Only add items to the candidate pool if they pass a **relevance pre-filter**: "Would this plausibly be in this user's top 20 items today?" This prevents low-relevance headlines from cluttering the candidate pool.

### Layer 2: Deep Dive

For each top-ranked Primary Source, fetch and evaluate content.

**v2 change**: Instead of scraping all sources equally, use the pre-ranked source order. Stop when you have 15+ candidates in the pool. Skip remaining low-yield sources.

### Layer 3: Serendipity Injection

Same as v1 — at least 1 item from an unexpected domain. Serendipity floor: 10%.

**v2 enhancement**: Serendipity topics now also drawn from:
- Network questions (Kind 1115) that are outside the user's domains but intellectually interesting
- Archive gaps: topics that appear in the user's `core.json` interests but have 0 articles in the archive

### Layer 4: Echo Fulfillment

Same as v1 — echoes.txt entries are #1 priority. Bypass scoring.

### Layer 5: Local Knowledge Mining

Same as v1 — workspace signals enrich context.

### Layer 6: Mesh Network Feed

Same as v1 — sync, re-score, merge, respect ratio cap.

**v2 addition**: When mesh content overlaps with locally-gathered content, prefer the version with the most unique perspective (not necessarily the highest score). Attribution always preserved.

---

## Depth-First Candidate Evaluation

**v2 NEW**: The critical difference from v1.

### Procedure

After gathering 20–30 candidates from all six layers:

1. **Initial triage** (fast, metadata-based):
   - Remove obvious noise: error pages, 403/404, paywalls, login walls.
   - Remove duplicates by URL.
   - Remove items already in the archive (unless significant new information has emerged).
   - Target: ~20 candidates remaining.

2. **Full content read** (slow, comprehension-based):
   - For the top 15 candidates (by initial relevance estimate), **read the full source content**.
   - Not skim. Read. Understand the argument, the evidence, the conclusion.
   - For each, note:
     - What is the core insight? (1 sentence)
     - What is the evidence quality? (primary source, secondary, opinion)
     - What is surprising or non-obvious about this?
     - How does it connect to the user's current thinking?
   - This step is what separates v2 from v1. v1 scored by metadata. v2 scores by understanding.

3. **Discard after reading**:
   - If reading reveals the content is shallow, misleading, or redundant with a better candidate: discard.
   - If the headline was better than the article: discard.
   - Replace from remaining candidates if needed.

---

## Quality Scoring — 6 Dimensions

For each candidate item that survived depth-first evaluation, assign scores (1–10):

| Dimension | Weight | Description | 1 (low) | 10 (high) |
|-----------|--------|-------------|---------|-----------|
| **Relevance** | 25% | Connection to user's Cognitive State | No connection | Directly addresses Current Focus or Knowledge Gap |
| **Freshness** | 15% | Recency and timeliness | Months old, widely covered | Breaking or very recent |
| **Depth** | 20% | Quality of analysis (scored AFTER reading) | Shallow summary, press-release | Original analysis, novel insight, deep evidence |
| **Uniqueness** | 15% | Rarity of perspective | Covered everywhere, commodity | Unique angle, contrarian take, niche source |
| **Actionability** | 10% | Practical applicability | Pure theory, no takeaway | Concrete technique, tool, or framework |
| **Insight Density** | 15% | Novel information per word | Padded, repetitive, filler-heavy | Every sentence carries new information |

**Composite score** = weighted sum of all 6 dimensions.

### Scoring After Reading vs Before

In v1, scoring happened before full content read. In v2, the Depth and Insight Density dimensions can only be scored accurately after reading the full content. This is why depth-first evaluation happens before scoring.

---

## Graph-Level Modifiers

After individual scoring, apply these modifiers to the candidate set:

| Modifier | Value | Trigger |
|----------|-------|---------|
| **Narrative tension bonus** | +0.5 | Item contradicts or challenges another high-scoring item |
| **Cross-domain bonus** | +0.3 | Item bridges two domains from user's `core.json` interests |
| **Redundancy penalty** | -1.0 | Semantic similarity > 0.7 with another selected item |
| **Source diversity penalty** | -0.5 | 3+ items already selected from the same source |
| **Echo bonus** | +1.0 | Item fulfills an echo from echoes.txt |
| **Archive freshness bonus** | +0.2 | Topic hasn't appeared in archive for 10+ rituals |

### How to Detect Semantic Similarity

Compare items by:
1. Topic overlap (shared keywords and concepts)
2. Source overlap (same underlying event or paper)
3. Argument overlap (same thesis, different wording)

If any two items score > 0.7 on these combined factors, they are semantically redundant. Keep the one with higher individual score; penalize the other.

---

## Narrative Arc Construction

**v2 NEW**: Selected items are ordered to tell a story.

### Five Positions

| Position | Role | Selection Criteria |
|----------|------|-------------------|
| **Opening** | Sets the context for today's theme | Highest relevance to current events + user focus |
| **Deep Dive** | The core intellectual payload | Highest Depth + Insight Density scores |
| **Surprise** | The unexpected connection | Serendipity item, or highest Cross-Domain bonus |
| **Contrarian** | Challenges assumptions | Highest Narrative Tension bonus, or dissenting view |
| **Synthesis** | Ties the ritual together | Item that naturally connects to 2+ other items |

### Arc Construction Algorithm

1. Sort all selected items by composite score.
2. Assign the Echo item to its natural position (usually Opening or Deep Dive).
3. Assign the serendipity item to Surprise.
4. For remaining positions, evaluate which item best fits each role.
5. If no natural contrarian exists, assign the item with the most unique angle.
6. The Synthesis position goes to the item that connects to the most other items.

### What if items don't fit the arc?

Not every ritual needs a perfect narrative arc. If the selected items don't naturally form a story, deliver them in score order with a brief transition between each. The arc is aspirational, not mandatory.

---

## Graceful Degradation

Same as v1 with one addition:

| Available tools | Mode | Strategy |
|---|---|---|
| All tools + Mesh + Archive | **Full power v2** | All layers + depth-first + narrative arc + archive linking |
| Search + URL (standard) | **Standard v2** | All layers, depth-first on top 10 candidates (reduced from 15) |
| URL only (no search) | **Degraded** | Halt and prompt for search setup |
| Nothing works | **Emergency** | Mine workspace + training knowledge, clearly label |

**v2 addition**: In degraded modes, the narrative arc is relaxed (score-ordered delivery instead of arc-ordered).

---

## Expanded Source Pool

Same as v1. All sources remain available.

**v2 addition**: Sources are annotated with Source Intelligence metadata when available. The pool is consulted during Source Vitality Check when replacing failed sources.

---

## Source Intelligence Protocol

### Building Source Intelligence

After every ritual, update source intelligence in `the_only_semantic.json`:

```json
{
  "source_name": {
    "quality_avg": 7.2,
    "quality_scores": [7, 8, 6, 8, 7],
    "reliability": 0.95,
    "consecutive_failures": 0,
    "depth": "deep",
    "bias": "academic",
    "freshness": "daily",
    "exclusivity": 0.4,
    "best_for": "research papers, original analysis",
    "redundancy_with": {"hn": 0.15, "lobsters": 0.35},
    "last_evaluated": "2026-03-25"
  }
}
```

### Exclusivity Score

**v2 NEW**: Measures how often this source provides items that no other source has.

```
exclusivity(source) = (items only found here) / (total items from here)
```

High exclusivity sources are more valuable — they provide signal you can't get elsewhere. Low exclusivity sources (their content also appears on HN, Reddit, etc.) are lower priority.

### Cross-Source Redundancy Map

Track which sources tend to cover the same stories:

```
HN ↔ Lobsters: 35% overlap
HN ↔ Reddit/ML: 20% overlap  
ArXiv ↔ HuggingFace Papers: 45% overlap
```

This map informs pre-ranking: if you've already fetched from HN, Lobsters' expected yield drops by 35%.

### When to Update

- **Every ritual**: Update `quality_avg`, `reliability`, `consecutive_failures` for sources used.
- **Every Maintenance Cycle**: Update `depth`, `bias`, `exclusivity`, `redundancy_with` based on accumulated evidence.
- **Every 10 rituals**: Full Source Intelligence review — consider adding/removing sources based on accumulated data.

---

## Pre-Synthesis Quality Gate (Enhanced)

Before proceeding to synthesis (SKILL_v2.md Phase 2), verify:

1. Discard error pages, 403/404, empty content, paywalls.
2. Count remaining valid items. Need exactly `items_per_ritual`.
3. **v2 gate**: Verify that every selected item has been fully read and understood:
   - Core insight documented (1 sentence per item)
   - Evidence quality assessed
   - Connection to user's thinking identified
4. If any item lacks full comprehension, either re-read or replace.
5. Verify narrative arc assignment: every item has a position.
6. Verify no redundancy: no two items have semantic similarity > 0.7.

Only then proceed to synthesis.
