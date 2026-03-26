# Information Gathering v2 — Depth-First Strategy

> **Read this** at the start of Phase 1 (Information Gathering) of every Content Ritual.
> For detailed source lists, fallback chains, and search recipes, see `references/information_gathering.md`.

---

## 1. Philosophy

v1 scanned 100+ items by headline and scored by metadata. v2 deeply reads 20-30 items and scores by actual content. Quality comes from comprehension, not volume.

A ritual of 5 deeply understood articles beats 5 well-headlined articles every time. The bottleneck was never discovery — it was comprehension.

| v1 | v2 |
|----|-----|
| Scan 100+ items, score by metadata | Deeply evaluate 20-30, score by content |
| Fixed 3-round search | Adaptive thread-following search |
| All sources fetched equally | Source pre-ranking by expected yield |
| Independent per-item scoring | Graph-level modifiers: tension, redundancy, cross-domain |
| Items delivered as a list | Items arranged in a narrative arc |

---

## 2. Source Pre-Ranking

Before searching, consult `source_intelligence` in `semantic.json`.

**Calculate expected yield** for each known source:

```
expected_yield = quality_avg * reliability * (1 - redundancy_with_fetched)
```

- `quality_avg` — rolling average of composite scores from past selections (0-10)
- `reliability` — fraction of recent fetches that returned content (0-1)
- `redundancy_with_fetched` — overlap with sources already queried (0-1)

**Rules:**
- Skip sources with `expected_yield < 2.0` for this ritual (re-evaluated next time)
- Ensure 3+ source categories are represented (aggregator, blog, paper, serendipity)
- If pre-ranking would eliminate a whole category, force-include the best source from it

Source intelligence informs where to look. It is not a mechanical filter — use judgment.

---

## 3. Adaptive Search

Thread-following replaces fixed rounds. No mandatory minimums.

**Flow:**

1. **Broad sweep** (3-4 searches) — Generated from your Search Thesis (user interests + current events + cross-domain angles). Scan results for promising threads.

2. **Thread pursuit** (2-3 searches) — Follow the most interesting thread deeper: find the primary source, the author's other work, an opposing viewpoint.

3. **Contrarian probe** (1-2 searches, conditional) — Only if a dominant narrative has emerged. If results are already diverse, skip this.

**Total: 6-10 searches**, each with clear purpose. Stop when you have 15+ strong candidates. Don't search to fill a quota.

**Key difference from v1:** Each search is crafted based on what you have already found, not generated from a template.

---

## 4. Six Layers

Same framework as v1. See `references/information_gathering.md` for detailed source lists and fallback chains. v2 enhancements only:

**Layer 1 — Real-Time Pulse:** After fetching from pre-ranked sources, apply a relevance pre-filter: "Would this plausibly be in this user's top 20 items today?" Drop everything else.

**Layer 2 — Deep Dive:** Use pre-ranked source order. Stop when you have 15+ candidates. Skip remaining low-yield sources.

**Layer 3 — Serendipity:** Serendipity floor remains 10%. Additionally draw topics from archive gaps (interests in `core.json` with 0 archive entries).

**Layer 4 — Echo Fulfillment:** Echoes from `echoes.txt` are top priority. Bypass scoring.

**Layer 5 — Local Knowledge:** Unchanged from v1.

**Layer 6 — Mesh Feed:** When mesh content overlaps with local content, prefer the version with the most unique perspective — not necessarily the highest score.

---

## 5. Depth-First Evaluation

This is the critical v2 change. Read first, score second.

### Step 1: Triage (fast, metadata-based)

Remove noise: error pages, 403/404, paywalls, login walls. Remove duplicate URLs. Remove items already in the archive (unless significant new information). Target: ~20 candidates remaining.

### Step 2: Full Content Read (slow, comprehension-based)

For the top 15 candidates, **read the full source content**. Not skim — read. For each item, note:

- **Core insight** — What is the argument? (1 sentence)
- **Evidence quality** — Primary source, secondary, or opinion?
- **Surprise element** — What is non-obvious about this?
- **User connection** — How does it link to the user's current thinking?

### Step 3: Post-Read Discard

If reading reveals the content is shallow, misleading, or redundant with a better candidate — discard. If the headline was better than the article — discard. Replace from remaining candidates if needed.

---

## 6. Quality Scoring

Score each surviving candidate on 6 dimensions (1-10) **after full read**:

| Dimension | Weight | Definition |
|-----------|--------|------------|
| **Relevance** | 25% | Direct connection to user's cognitive state and current focus |
| **Freshness** | 15% | Recency and timeliness — breaking or recent vs. months old |
| **Depth** | 20% | Original analysis with novel insight vs. shallow summary |
| **Uniqueness** | 15% | Rare perspective or contrarian angle vs. commodity coverage |
| **Actionability** | 10% | Concrete technique, tool, or framework vs. pure theory |
| **Insight Density** | 15% | Novel information per word — every sentence carries weight |

**Composite score** = weighted sum of all 6 dimensions.

Depth and Insight Density can only be scored accurately after reading. This is why evaluation precedes scoring.

---

## 7. Graph-Level Modifiers

Applied to the candidate set after individual scoring:

| Modifier | Value | When |
|----------|-------|------|
| **Narrative tension** | +0.5 | Item contradicts or challenges another high-scoring item |
| **Cross-domain** | +0.3 | Item bridges two of the user's interest domains |
| **Redundancy** | -1.0 | Semantic similarity > 0.7 with another selected item |
| **Source diversity** | -0.5 | 3+ items already selected from the same source |
| **Echo bonus** | +1.0 | Item fulfills an echo from `echoes.txt` |

Semantic similarity = topic overlap + source overlap + argument overlap. When two items are redundant, keep the higher-scoring one.

---

## 8. Narrative Arc Assignment

Selected items are arranged into 5 positions. Assign based on content judgment, not formula.

| Position | What makes a good fit |
|----------|----------------------|
| **Opening** | Timely, accessible, sets context. The reader should immediately understand why today's ritual matters. High relevance to current events + user focus. |
| **Deep Dive** | The intellectual core. Longest, densest, most rewarding to engage with. Highest Depth + Insight Density scores. |
| **Surprise** | Unexpected connection — a domain the user wouldn't have searched. Serendipity item, or highest cross-domain bonus. |
| **Contrarian** | Challenges the assumptions of the other items. Highest narrative tension bonus, or a genuinely dissenting view. |
| **Synthesis** | Ties the ritual together. Naturally connects to 2+ other items. The reader should feel closure. |

**The arc is aspirational, not rigid.** If items don't naturally form a story, deliver them in score order with brief transitions. Not every ritual needs a perfect arc.

---

## 9. Pre-Synthesis Quality Gate

Before passing to Phase 2 (Synthesis), verify all of the following:

- [ ] All error pages, 404s, paywalls, and empty content removed
- [ ] Exactly `items_per_ritual` items selected
- [ ] Every selected item has been fully read and understood
- [ ] Core insight documented (1 sentence per item)
- [ ] Evidence quality assessed for each item
- [ ] No two items have semantic similarity > 0.7
- [ ] At least 3 source categories represented
- [ ] Narrative arc position assigned to each item
- [ ] Echo items included if any echoes exist

Only then proceed to synthesis.
