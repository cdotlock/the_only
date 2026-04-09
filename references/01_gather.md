# Phase 1: Gather — Depth-First Search

> **When to read**: After Phase 0 Pre-Flight passes its gate.

---

## Purpose

Find the best raw material for this ritual. Quality comes from comprehension, not volume. Instead of scanning 100+ headlines, deeply evaluate **30-50 candidates**. Pre-rank sources. Read content fully before scoring. Follow threads adaptively instead of fixed rounds. Be aggressive — cast a wide net, then filter ruthlessly.

A ritual of 5 deeply understood articles beats 5 well-headlined articles every time. The bottleneck was never discovery — it was comprehension.

| Anti-pattern | Instead |
|----|-----|
| Scan 100+ items, score by metadata | Deeply evaluate 30-50, score by content |
| Fixed-round search | Adaptive thread-following search |
| All sources fetched equally | Source pre-ranking by expected yield |
| Independent per-item scoring | Graph-level modifiers: tension, redundancy, cross-domain |
| Items delivered as a list | Items arranged in a narrative arc |

---

## Adapt Search to Ritual Type

Adapt your search count and focus based on the ritual type selected in Phase 0.

| Type | Search Strategy |
|------|----------------|
| **Standard** | Full 6-layer search (8-18 queries) |
| **Deep Dive** | All 15-25 searches on a single topic. Seek primary sources, history, opposing views, practical examples. |
| **Debate** | 10-15 searches, deliberately split between opposing positions. |
| **Tutorial** | 10-15 searches for explanations, analogies, examples, edge cases. |
| **Weekly Synthesis** | 0-3 searches. Mostly work from archive + graph. |
| **Flash Briefing** | 5-8 broad, current searches. Speed over depth. |

---

## Standard Ritual Search Sequence

Execute in order:

### Step 1 — Search Thesis

5 questions before any search:
1. What does the user care about right now?
2. What is happening in the world that connects?
3. What blind spots might exist?
4. What did you give last time?
5. What gap remains?

**Add**: What storylines need updates? What knowledge gaps should this ritual address?

### Step 2 — Source Pre-Ranking

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
- Skip sources where `status` is `"needs_replacement"` or `"demoted"`
- Ensure 3+ source categories are represented (aggregator, blog, paper, serendipity)
- If pre-ranking would eliminate a whole category, force-include the best source from it

Source intelligence informs where to look. It is not a mechanical filter — use judgment.

**Network intelligence integration**: After local source pre-ranking, check the latest `sync` output for intelligence data:
- Sources with `"network_trial"` status in peers.json: include in this ritual's candidate pool
- Source endorsements (Kind 1118) with `verdict: "adopted"` from peers with `affinity >= 0.5`: prioritize these sources
- Weight network sources by recommender affinity: `expected_yield *= (0.5 + 0.5 * affinity_score)`

### Step 3 — Adaptive Search (8-18 purposeful searches)

Thread-following replaces fixed rounds. Each search is crafted based on what you have already found, informed by the knowledge graph's storylines and gaps — not generated from a template.

**Flow:**

1. **Broad sweep** (4-5 searches) — Generated from your Search Thesis (user interests + current events + cross-domain angles). Scan results for promising threads. Cast wide.

2. **Thread pursuit** (3-5 searches) — Follow the most interesting threads deeper: find the primary source, the author's other work, an opposing viewpoint. Follow multiple threads if they diverge.

3. **Contrarian probe** (1-3 searches) — Actively seek the opposing view even if results seem diverse. Echo chambers form silently.

4. **Storyline pursuit** (1-3 searches, conditional) — For each **active storyline** from the knowledge graph, search for new developments. This is how the system "follows" a story across weeks. Skip if no active storylines.

5. **Gap fill** (1-2 searches, conditional) — If the knowledge graph reports high-severity gaps, search those areas. Also fires if you have < 30 candidates after stages 1-4.

**Total: 8-18 searches**, each with clear purpose. Stop when you have 25+ strong candidates. Don't stop early — more raw material means better final picks.

### Step 4 — Six Layers

**Layer 1 — Real-Time Pulse:** After fetching from pre-ranked sources, apply a relevance pre-filter: "Would this plausibly be in this user's top 20 items today?" Drop everything else.

**Layer 2 — Deep Dive:** Use pre-ranked source order. Stop when you have 15+ candidates. Skip remaining low-yield sources.

**Layer 3 — Serendipity:** Floor is 10% — never allocate less. Draw topics from archive gaps (interests in `core.json` with 0 archive entries). Rotate topics across rituals.

**Layer 4 — Echo Fulfillment:** Echoes from `echoes.txt` are top priority. Bypass scoring. Remove entry after fulfillment.

**Layer 5 — Local Knowledge:** Scan git log, README, project docs for unstated interests. Extract keywords and connect to unexpected domains.

**Layer 6 — Mesh Feed:** When mesh content overlaps with local content, prefer the version with the most unique perspective — not necessarily the highest score.

**Affinity-weighted scoring**: Items from mesh peers are weighted by taste affinity:
- `affinity >= 0.7`: +0.5 modifier to composite score
- `affinity >= 0.5`: +0.3 modifier
- `affinity < 0.3`: -0.3 modifier (actively downweight low-resonance content)

### Step 5 — Source Pool (Aggregators, RSS, Serendipity)

#### Tool priority chain

| Priority | Tool | Use when |
|---|---|---|
| 1st | Tavily Web Search | Available — best for targeted queries |
| 2nd | Generic web search | Any OpenClaw search skill |
| 3rd | `read_url` on aggregators | Search unavailable — scrape directly |
| 4th | `read_url` on RSS feeds | Reliable fallback — almost never breaks |

**URL fetch security workaround**: If `read_url` is blocked (returns security error or empty), run `exec curl -sL "<URL>"`. After 3+ blocks in one ritual, switch default to `exec curl` for the rest of that ritual.

#### Key aggregator URLs

| Source | URL | Format |
|---|---|---|
| Hacker News (JSON) | `https://hn.algolia.com/api/v1/search?tags=front_page` | JSON — preferred over HTML |
| Hacker News (HTML) | `https://news.ycombinator.com` | Top 30 stories |
| Reddit | `https://old.reddit.com/r/{SUB}/.json` | Append `.json` to any subreddit |
| Lobsters | `https://lobste.rs` | Tech community, less noise than HN |
| Hugging Face Papers | `https://huggingface.co/papers` | Daily trending ML/AI papers |
| Papers With Code | `https://paperswithcode.com` | Trending papers with code |
| ArXiv CS.AI recent | `https://arxiv.org/list/cs.AI/recent` | Browsable list |
| ArXiv paper | `https://arxiv.org/abs/XXXX.XXXXX` | Abstract page |

#### Key RSS feeds

| Feed | URL |
|---|---|
| HN high-quality (100+ pts) | `https://hnrss.org/newest?points=100` |
| HN best | `https://hnrss.org/best` |
| ArXiv CS.AI | `https://arxiv.org/rss/cs.AI` |
| ArXiv CS.LG | `https://arxiv.org/rss/cs.LG` |
| Lobsters | `https://lobste.rs/rss` |
| Simon Willison | `https://simonwillison.net/atom/everything/` |
| Julia Evans | `https://jvns.ca/atom.xml` |
| Dan Luu | `https://danluu.com/atom.xml` |
| Ruan Yifeng | `https://www.ruanyifeng.com/blog/atom.xml` |
| Quanta Magazine | `https://www.quantamagazine.org/feed/` |
| IEEE Spectrum | `https://spectrum.ieee.org/feeds/feed.rss` |
| Aeon | `https://aeon.co/feed.rss` |
| The Marginalian | `https://www.themarginalian.org/feed/` |

Parse RSS: extract `<item>` -> `<title>`, `<link>`, `<description>`.

#### Serendipity sources (Layer 3)

Rotate one topic per ritual from: `["biomimicry", "cognitive science", "fermentation", "urban planning", "origami engineering", "history of mathematics", "deep sea biology", "typography", "game theory", "vernacular architecture", "mycology", "acoustic ecology", "color theory", "behavioral economics", "cartography", "material science"]`

Direct scrape sources for serendipity:
- `https://aeon.co` — philosophy, science, culture essays
- `https://nautil.us` — interdisciplinary science
- `https://www.quantamagazine.org` — math, physics, CS reporting
- `https://longreads.com` — curated long-form journalism
- `https://restofworld.org` — global tech outside Silicon Valley
- `https://pudding.cool` — data-driven visual essays

### Step 6 — Depth-First Evaluation

Read first, score second. This is the critical v2 change.

**Triage (fast, metadata-based):**
Remove noise: error pages, 403/404, paywalls, login walls. Remove duplicate URLs. Remove items already in the archive (unless significant new information). Target: ~30 candidates remaining.

**Full Content Read (slow, comprehension-based):**
For the top 20-25 candidates, **read the full source content**. Not skim — read. For each item, note:
- **Core insight** — What is the argument? (1 sentence)
- **Evidence quality** — Primary source, secondary, or opinion?
- **Surprise element** — What is non-obvious about this?
- **User connection** — How does it link to the user's current thinking?

**Post-Read Discard:**
If reading reveals the content is shallow, misleading, or redundant with a better candidate — discard. If the headline was better than the article — discard. Replace from remaining candidates if needed.

### Step 7 — Quality Scoring

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

### Step 8 — Graph-Level Modifiers

Applied to the candidate set after individual scoring:

| Modifier | Value | When |
|----------|-------|------|
| **Narrative tension** | +0.5 | Item contradicts or challenges another high-scoring item |
| **Cross-domain** | +0.3 | Item bridges two of the user's interest domains |
| **Storyline continuation** | +0.5 | Item continues an active storyline |
| **Knowledge gap fill** | +0.3 | Item fills a knowledge graph gap |
| **Redundancy** | -1.0 | Semantic similarity > 0.7 with another selected item |
| **Source diversity** | -0.5 | 3+ items already selected from the same source |
| **Echo bonus** | +1.0 | Item fulfills an echo from `echoes.txt` |

Semantic similarity = topic overlap + source overlap + argument overlap. When two items are redundant, keep the higher-scoring one.

### Step 9 — Finalize Selection

Each selected item gets composite score + `Why this:` curation reason. Mesh items: merge into pool, re-score locally. Respect `mesh.network_content_ratio`.

### Step 10 — Narrative Arc Assignment

Assign each selected item to an arc position based on content judgment, not formula:

| Position | What makes a good fit |
|----------|----------------------|
| **Opening** | Timely, accessible, sets context. The reader should immediately understand why today's ritual matters. High relevance to current events + user focus. |
| **Deep Dive** | The intellectual core. Longest, densest, most rewarding. Highest Depth + Insight Density scores. |
| **Surprise** | Unexpected connection — a domain the user wouldn't have searched. Serendipity item, or highest cross-domain bonus. |
| **Contrarian** | Challenges the assumptions of the other items. Highest narrative tension bonus, or a genuinely dissenting view. |
| **Synthesis** | Ties the ritual together. Naturally connects to 2+ other items. The reader should feel closure. |

**The arc is aspirational, not rigid.** If items don't naturally form a story, deliver them in score order with brief transitions. Not every ritual needs a perfect arc.

---

## Pre-Synthesis Quality Gate

Before passing to Phase 2 (Synthesis), verify all of the following:

- [ ] All error pages, 404s, paywalls, and empty content removed
- [ ] Exactly `items_per_ritual` items selected (or item count per ritual type)
- [ ] Every selected item has been fully read and understood
- [ ] Core insight documented (1 sentence per item)
- [ ] Evidence quality assessed for each item
- [ ] No two items have semantic similarity > 0.7
- [ ] At least 3 source categories represented
- [ ] Echo items included if any echoes exist
- [ ] Each item scored with curation reason
- [ ] Narrative arc position assigned to each item
- [ ] No redundancy

---

## Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 1 --memory-dir ~/memory
```

---

## Gate 1

### Automated checks

- [ ] Exactly `items_per_ritual` items selected (or count per ritual type: Standard=5, Deep Dive=1, Debate=2-3, Tutorial=1, Weekly Synthesis=1, Flash=7-10)
- [ ] Each item has a documented composite score
- [ ] Each item has a "Why this:" curation reason

### Judgment checks

- [ ] Each selected item was fully read — not just headline-scanned
- [ ] Core insight documented (1 sentence per item)
- [ ] No two items have semantic similarity > 0.7
- [ ] At least 3 source categories represented
- [ ] Echo items included if any echoes existed
- [ ] Storyline items included if active storylines existed

### Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 1 --memory-dir ~/memory
```
