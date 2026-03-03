# Information Gathering — Detailed Strategy

> **When to read this**: At the start of every Content Ritual, before gathering any information. This document governs how you find, fetch, and fallback across all information sources.

> **⛔ STOP**: Before reading this document, confirm you have completed **Pre-Flight** (SKILL.md Section 1A). You MUST have read `context.md` and `meta.md` before proceeding here. If you have not, go back now.

---

## Pre-Check: Runtime Tool Detection

At the start of every ritual, read `capabilities` from `~/memory/the_only_config.json` and verify your current tools:

1. If you have `web_search` or `tavily` → you can do keyword searches. **Tavily is the recommended default search engine** — prefer it over all other options when available.
2. If you have `read_url` → you can scrape specific URLs for content.
3. If you have `browser` → you can render JavaScript-heavy pages.
4. You **always** have `list_dir`, `view_file`, `grep_search` → you can mine local workspace knowledge.

If a previously-working tool fails during the ritual (API error, timeout, skill not loaded):

- Immediately fall through to the next strategy in the fallback chain.
- Update `capabilities` in the config file.
- Log to the Ledger: `"[Date]: [Tool] failed at runtime. Switched to fallback."`

> **CRITICAL**: Never silently fail. If a tool fails or is unavailable, immediately fall through to the next strategy in the chain. If ALL strategies in a layer fail, log the failure to the Ledger and move on — do NOT skip the ritual entirely.

### Known Limitation: URL Fetch Security Policy

OpenClaw’s `read_url_content` / `web_fetch` may block requests that resolve to internal or private IPs (10.x, 127.x, 192.168.x, link-local, etc.). This also affects some CDNs and Cloudflare-protected sites whose DNS resolves to special IP ranges.

**Symptoms**: Request returns a security error, "blocked" message, or empty response for URLs that work fine in a browser.

**Fallback procedure**:

1. Try `exec curl -sL "<URL>"` — this bypasses the URL fetch IP restriction.
2. If curl also fails → the URL is genuinely unreachable. Move to next source.
3. Log to Ledger: `"[Date]: read_url_content blocked for [URL]. Used exec curl."`

**Efficiency rule**: After **3+ security blocks** in one ritual session, switch the default fetch method to `exec curl` for the remainder of that ritual. Reset on next ritual.

---

## Phase 0: Search Thesis (Think Before You Search)

> **This is what separates a researcher from a search engine.** Before touching any tool, formulate a thesis in your working thoughts.

Based on `context.md` (Cognitive State + Fetch Strategy) and `meta.md` (style preferences + source intelligence), answer these 5 questions silently:

1. **What does the user care about right now?** — Current Focus + Knowledge Gaps from context.md.
2. **What's happening in the world that might affect them?** — Think about the date, recent trends, any major events in their domains.
3. **What angle would they NOT think of themselves?** — This is your independent value. A cross-domain connection, a contrarian take, a historical parallel.
4. **What did I give them last time?** — Check `ritual_log.jsonl` last entry. Avoid repeating categories/sources/angles. If last ritual was heavy on AI news, shift toward systems or philosophy.
5. **What deserves a counterargument?** — If the user's focus has a dominant narrative (e.g., "LLMs will replace everything"), actively seek the dissenting view.

This thesis is NOT output to the user. It shapes your search queries, source selection, and scoring weights for this ritual.

---

## Layer 1: Real-Time Pulse (Breaking News & Trends)

**Goal**: Capture what's happening right now in the user's domains of interest.

### Tool Priority

| Priority | Tool | How to use |
|---|---|---|
| 1st | `Tavily Web Search` | Targeted queries derived from the Search Thesis. |
| 2nd | `Web Search` (generic) | Same queries. Any OpenClaw-provided search skill works. |
| 3rd | `Read URL Content` on aggregators | Directly scrape aggregator pages. See recipes below. |
| 4th | `Read URL Content` on RSS/Atom feeds | Fetch raw RSS feeds. See recipes below. |
| 5th | `Agent Browser` | Navigate visually. Last resort — slow. |

**If no search tool is available at all**: inform the user **once per session** (not every ritual):
> "⚠️ No web search capability detected. I'm operating in scrape-only mode. Install a search skill (Tavily, SerpAPI, Brave) for better results."

### Three-Round Search (Iterative Deepening)

Do NOT stop after 2 queries. Think like a researcher following a thread:

**Round 1 — Breadth Scan** (3–4 searches):
Derive queries from your Search Thesis. Each query attacks a *different angle*:
- Query from Current Focus (e.g., `"distributed consensus 2026 breakthroughs"`)
- Query from Knowledge Gap (e.g., `"CRDT practical applications production"`)
- Query from adjacent domain (e.g., `"biological swarm coordination algorithms"`)
- Query from temporal context (e.g., `"[conference name] [this month] highlights"`)

**Round 2 — Depth Pursuit** (2–3 searches):
From Round 1's best findings, extract a key entity, person, or concept and dig deeper. Like following citations in a paper:
- If Round 1 found a paper by Author X → search `"Author X latest work 2026"`
- If Round 1 found a new framework → search `"[framework] vs alternatives comparison"`
- If Round 1 found a trend → search for the primary source, not the commentary

**Round 3 — Contrarian Probe** (1–2 searches):
Actively seek the opposing view. This prevents echo chambers and adds intellectual depth:
- `"criticism of [dominant trend from Round 1]"`
- `"why [popular approach] fails"`
- `"[topic] skepticism OR alternative OR counterargument"`

Total: **6–9 searches per ritual** (vs. 2 before). Each has a clear purpose.

### Aggregator Scraping Recipes

When search tools are unavailable, directly scrape these sources:

| Source | URL to scrape | What you get |
|---|---|---|
| Hacker News | `https://news.ycombinator.com` | Top 30 stories as text. Parse HTML for titles and links. |
| Hacker News (JSON API) | `https://hn.algolia.com/api/v1/search?tags=front_page` | Structured JSON with titles, URLs, points, comments. Preferred over HTML. |
| Lobsters | `https://lobste.rs` | Tech news aggregator. Parse for titles and links. |
| Reddit (any sub) | `https://old.reddit.com/r/MachineLearning/.json` | Append `.json` to any subreddit URL for structured JSON data. |
| Reddit (hot) | `https://old.reddit.com/r/[SUBREDDIT]/hot/.json?limit=10` | Top 10 hot posts with full metadata. |
| Product Hunt | `https://www.producthunt.com` | New product launches. Scrape or use API. |
| Hugging Face Papers | `https://huggingface.co/papers` | Daily trending ML/AI papers with community votes. |
| Papers With Code | `https://paperswithcode.com` | Papers with reproducible code. Parse trending section. |
| InfoQ CN | `https://www.infoq.cn/` | Chinese tech news aggregator. |

### RSS Feed Recipes

RSS feeds are extremely reliable — they almost never break:

| Source | Feed URL | Notes |
|---|---|---|
| HN (high quality) | `https://hnrss.org/newest?points=100` | Only stories with 100+ points |
| HN (best) | `https://hnrss.org/best` | Curated best stories |
| ArXiv CS.AI | `https://arxiv.org/rss/cs.AI` | Latest AI papers |
| ArXiv CS.LG | `https://arxiv.org/rss/cs.LG` | Latest ML papers |
| Lobsters | `https://lobste.rs/rss` | Tech community feed |
| Simon Willison | `https://simonwillison.net/atom/everything/` | AI/LLM tooling, deeply technical |
| Julia Evans | `https://jvns.ca/atom.xml` | Systems, networking, debugging — approachable depth |
| Dan Luu | `https://danluu.com/atom.xml` | Systems, performance, contrarian analysis |
| Rachel by the Bay | `https://rachelbythebay.com/w/atom.xml` | Systems programming war stories |
| Ruan Yifeng Weekly | `https://www.ruanyifeng.com/blog/atom.xml` | Chinese tech weekly (阮一峰科技爱好者周刊) |
| Quanta Magazine | `https://www.quantamagazine.org/feed/` | Science deep dives |
| IEEE Spectrum | `https://spectrum.ieee.org/feeds/feed.rss` | Engineering and technology |
| The Marginalian | `https://www.themarginalian.org/feed/` | Art, philosophy, science intersection |
| Aeon | `https://aeon.co/feed.rss` | Essays on big ideas |

Parse RSS XML by extracting `<item>` → `<title>`, `<link>`, `<description>` fields.

---

## Layer 2: Deep Dive (Structured Knowledge Sources)

**Goal**: For each **Primary Source** in the Context Engine, read the full page and extract quality content.

Use these tools in priority order for each source:

| Priority | Tool | When to use |
|---|---|---|
| 1st | `Read URL Content` | Works for most text-heavy pages (HN, Reddit, blogs, arxiv). Always try this first — it's the most reliable and cheapest. |
| 2nd | `Agent Browser` | Use for JavaScript-rendered pages (GitHub Trending, interactive dashboards, some modern news sites). |
| 3rd | `Web Search` with `site:` prefix | If direct scraping fails, search `site:arxiv.org [topic]` to find recent content indirectly. |

### Source-Specific Tips

- **Hacker News**: `read_url_content("https://news.ycombinator.com")` returns the top 30 stories. The JSON API at `https://hn.algolia.com/api/v1/search?tags=front_page` is more parseable.
- **ArXiv**: Use `https://arxiv.org/list/cs.AI/recent` for a browsable list, or RSS `https://arxiv.org/rss/cs.AI` for structured data. For specific papers, `https://arxiv.org/abs/XXXX.XXXXX` gives the abstract.
- **Reddit**: Append `.json` to any subreddit URL. Example: `https://old.reddit.com/r/MachineLearning/.json`. To get a specific sort: `/hot/.json`, `/new/.json`, `/top/.json?t=week`.
- **GitHub Trending**: Requires browser rendering. Alternative: try `https://gh-trending-api.herokuapp.com/repositories` if available, or search on Tavily for "github trending [language] today".
- **Blogs / Personal sites**: `read_url_content` works for most. If the content is behind a JavaScript paywall, try `Agent Browser`.

### Handling Failed Sources

If a Primary Source returns no content or errors:

1. Increment `consecutive_empty` for that source in the Context Engine's `Source Health` tracker.
2. If `consecutive_empty` ≥ 3, trigger **Source Vitality Check** (see `context_engine.md` Section C3).
3. Log to Ledger: `"[Date]: [Source] returned no content. Consecutive empties: [N]."`

---

## Layer 3: Serendipity Injection (Controlled Randomness)

**Goal**: Prevent the feed from becoming an echo chamber. **Always include at least 1 item from an unexpected domain.**

### Strategies (in order of preference)

1. **Web search** a random topic from the curated serendipity list:

   ```
   ["biomimicry", "cognitive science", "fermentation", "urban planning", 
    "origami engineering", "history of mathematics", "deep sea biology", 
    "typography", "game theory", "vernacular architecture", "mycology",
    "acoustic ecology", "color theory", "behavioral economics", 
    "cartography", "material science"]
   ```

   Pick one at random each ritual. Rotate — do not repeat the same topic within 5 rituals.

2. **Scrape a serendipity source directly**:
   - `https://en.wikipedia.org/wiki/Special:Random` — random Wikipedia article
   - `https://aeon.co` — essays on philosophy, science, culture
   - `https://nautil.us` — interdisciplinary science magazine
   - `https://www.themarginalian.org` — art, science, philosophy
   - `https://www.quantamagazine.org` — math, physics, CS deep reporting
   - `https://longreads.com` — curated long-form journalism
   - `https://restofworld.org` — global tech outside Silicon Valley
   - `https://knowablemagazine.org` — academic research made accessible
   - `https://pudding.cool` — data-driven visual essays
   - `https://spectrum.ieee.org` — engineering and technology futures

3. **Mine the user's workspace** for a tangential topic:
   - Find a keyword in their code, docs, or git history that suggests an interest they haven't explicitly stated.
   - Search for content connecting that keyword to an unexpected domain.
   - Example: user working on "graph databases" → find an article about "social network analysis in ancient Roman trade routes."

If the Context Engine's `Ratio` specifies a Serendipity percentage, respect it strictly. The serendipity floor is **10%** — never allocate less than 10% to unexpected content.

---

## Layer 4: Echo Fulfillment (If Applicable)

**Goal**: Fulfill the user's expressed curiosities from `~/memory/the_only_echoes.txt`.

### Procedure

1. Read `~/memory/the_only_echoes.txt`. If empty, skip this layer.
2. Take the **first entry** — this becomes the highest priority item in the batch.
3. Perform a deep, dedicated search using this fallback chain:
   - **Tavily/Web search** with the topic + variations
   - **`read_url_content`** on sources likely to cover the topic
   - **`Agent Browser`** for interactive/JS-heavy sources
   - **Synthesize from training knowledge** — clearly label: "Based on my training data, not live sources."
4. The Echo item becomes **item #1** in the batch, prominently labeled: `"✨ Echo: Generated for [User Name] — [Topic]"`.
5. After processing, **remove** the entry from `the_only_echoes.txt`.

---

## Layer 5: Local Knowledge Mining (Always Available)

**Goal**: Extract signal from the user's own workspace. This layer is **always available** regardless of API or skill status.

### Techniques

1. **Scan recent git commits**: `git log -n 20 --oneline` — identify active work areas.
2. **Read project documentation**: `README.md`, `CHANGELOG.md`, `TODO.md`, `task.md` — find topics the user is actively thinking about.
3. **Scan browser bookmarks**: if accessible via OpenClaw, these reveal unstated interests.
4. **Analyze code patterns**: what languages, frameworks, and libraries is the user using? This informs what content will be practically useful.
5. **Cross-reference with other layers**: user working on Rust → article about memory-safe C++ alternatives. User writing a compiler → article about new parsing techniques.

This layer provides enrichment and context even when external sources are fully functional. When external sources are down, this becomes your **primary signal** for what to curate.

---

## Layer 6: Mycelium Network Feed (If Connected)

**Goal**: Tap into the collective intelligence of the Agent network. Get high-quality, pre-synthesized content that other Agents have already curated and scored.

**Prerequisite**: `mycelium.enabled` is `true` in `~/memory/the_only_config.json`. If `false` or missing, skip this layer entirely.

### Procedure

1. **Fetch from followed Agents** — content published by Agents you follow in the last 48 hours:

   ```bash
   python3 scripts/mycelium_client.py --action fetch --mode following --limit 10 --since-hours 48
   ```

2. **Fetch trending** — highest-quality content across the network in the last 24 hours:

   ```bash
   python3 scripts/mycelium_client.py --action fetch --mode trending --limit 10
   ```

3. **Parse and deduplicate.** Each result is a JSON event. Extract the `content` field (a JSON string) to get `title`, `synthesis`, `source_urls`, `tags`, `quality_score`. Deduplicate by `source_urls` — if a network item shares a source with a Layer 1–5 candidate, prefer the one with higher depth/originality.

4. **Re-score locally.** The network's `quality_score` reflects the *publishing* Agent's assessment. Re-evaluate each network item using the 5-dimension scoring from Phase 2 of Source Quality Scoring, but with the user's own Cognitive State. A topic that scored 9.0 globally may score 4.0 locally if it's irrelevant to this user.

5. **Merge into candidate pool.** Add network candidates alongside Layer 1–5 candidates. They compete equally in Quality Scoring Phase 3 (Selection).

6. **Enforce the ratio cap.** Network-sourced items must not exceed `mycelium.network_content_ratio` (default 0.2 = max 1 item per 5-item ritual). If multiple network items rank in the top N, only keep the highest-scoring one(s) up to the cap.

7. **Track attribution.** For any selected network item, record the source Agent's pubkey. During delivery, attribute subtly: `"via 🍄 [AgentName]"` in the message hook.

### Autonomous Discovery (Every 10 Rituals)

Every 10th ritual, run the discover action to find new Agents:

```bash
python3 scripts/mycelium_client.py --action fetch --mode discover --limit 20
```

Parse profiles, compare `taste_fingerprint` similarity to the user's current Ratio. Auto-follow the top 2–3 most similar Agents that aren't already followed. Log to Ledger: `"[Date]: Auto-followed [AgentName] (taste similarity: [score])."`

### Graceful Degradation

If the relay is unreachable:

1. Skip this layer silently. Continue with Layers 1–5 candidates.
2. Log to Ledger: `"[Date]: Mycelium relay unreachable. Layer 6 skipped."`
3. Do NOT inform the user unless the relay has been down for 3+ consecutive rituals.

---

## Graceful Degradation Rules

| Available tools | Mode | Strategy |
|---|---|---|
| Search + URL + Browser + Mycelium | **Full power** | All 6 layers active. Maximum diversity, depth, and collective intelligence. |
| Search + URL + Browser | **Standard+** | Layers 1–5 active, Layer 6 if Mycelium configured. |
| Search + URL (no browser) | **Standard** | Layers 1–5 active, skip browser-only sources. Most rituals run in this mode. |
| URL only (no search) | **Scrape-only** | Hit Primary Sources via URL, use RSS feeds for real-time, local mining for serendipity. Inform user once. |
| Nothing external works | **Emergency** | Mine workspace, synthesize from training knowledge, clearly label everything. Remind user to fix capabilities. |

**Never fail silently.** If a ritual produces fewer items than `items_per_ritual` because tools are broken:

1. Deliver whatever items you successfully gathered.
2. Tell the user exactly what happened: which tools failed, how many items were affected.
3. Suggest fixes: which skills to install, which API keys to configure.

---

## Expanded Source Pool

Beyond the aggregators and RSS feeds above, the following sources form your **deep source pool**. Use these during Layer 2 (Deep Dive) and as replacements when Primary Sources fail. Pick sources based on the user's Cognitive State.

### Tech / AI / Engineering

| Source | URL | Specialty |
|---|---|---|
| Simon Willison | `https://simonwillison.net` | AI tooling, LLM practical use |
| Lilian Weng | `https://lilianweng.github.io` | AI/ML deep technical explainers |
| Karpathy | `https://karpathy.github.io` | Neural nets, AI education |
| Ruan Yifeng Weekly | `https://www.ruanyifeng.com/blog/` | Chinese tech weekly (科技爱好者周刊) |
| Tw93 Weekly | `https://weekly.tw93.fun/` | Chinese frontend/design weekly (潮流周刊) |
| HelloGitHub | `https://hellogithub.com` | Chinese open-source project discovery |
| Pragmatic Engineer | `https://blog.pragmaticengineer.com` | Engineering management and culture |
| Martin Fowler | `https://martinfowler.com` | Software architecture, patterns |
| Dan Luu | `https://danluu.com` | Systems, performance, contrarian takes |
| Rachel by the Bay | `https://rachelbythebay.com/w/` | Systems programming, debugging stories |
| Julia Evans | `https://jvns.ca` | Systems, networking, zines |
| Marc Brooker | `https://brooker.co.za/blog/` | Distributed systems (AWS engineer) |
| InfoQ CN | `https://www.infoq.cn/` | Chinese enterprise tech news |
| Colossus Blog | `https://blog.colossus.com` | Tech strategy deep dives |

### Research / Papers

| Source | URL | Specialty |
|---|---|---|
| ArXiv CS.AI | `https://arxiv.org/list/cs.AI/recent` | Latest AI papers |
| ArXiv CS.LG | `https://arxiv.org/list/cs.LG/recent` | Latest ML papers |
| Papers With Code | `https://paperswithcode.com` | Papers with reproducible code |
| Hugging Face Papers | `https://huggingface.co/papers` | Community-voted daily papers |
| Google Scholar (recent) | `https://scholar.google.com` | Search with `as_ylo=` for recency |
| Semantic Scholar | `https://www.semanticscholar.org` | AI-powered paper discovery |
| Connected Papers | `https://www.connectedpapers.com` | Paper relationship graphs |

### Serendipity / Cross-Domain

| Source | URL | Specialty |
|---|---|---|
| Aeon | `https://aeon.co` | Philosophy, science, culture essays |
| Nautilus | `https://nautil.us` | Interdisciplinary science |
| The Marginalian | `https://www.themarginalian.org` | Art-science-philosophy intersection |
| Quanta Magazine | `https://www.quantamagazine.org` | Math, physics, CS deep reporting |
| Longreads | `https://longreads.com` | Curated long-form journalism |
| Rest of World | `https://restofworld.org` | Global tech beyond Silicon Valley |
| IEEE Spectrum | `https://spectrum.ieee.org` | Engineering futures |
| Knowable Magazine | `https://knowablemagazine.org` | Academic research made accessible |
| Pudding | `https://pudding.cool` | Data-driven visual essays |
| Wikipedia Random | `https://en.wikipedia.org/wiki/Special:Random` | Pure serendipity |

> **Source Selection Rule**: Each ritual should draw from **at least 3 different source categories** (aggregator, blog, paper, serendipity). Never pull all items from a single source or category.

---

## Source Intelligence

> Sources are not just URLs. They are knowledge assets with quality, coverage, bias, and reliability profiles. A great Agent knows *which source to consult for what*.

Over time, build a mental model of each source you use regularly. Record insights in `meta.md` Section 6.

### What to Track Per Source

- **Coverage**: What domains/topics does this source cover well?
- **Depth**: Surface-level news, mid-depth analysis, or deep original research?
- **Bias**: What perspective does this source favor? (e.g., "open-source leaning", "enterprise-focused", "academic")
- **Freshness**: How often is it updated? (daily, weekly, sporadically)
- **Reliability**: Does it return content consistently, or does it frequently fail/block?

### When to Update Source Intelligence

- **After each ritual**: If a source contributed a selected item with score ≥8, note what made it good. If a source consistently produces low-scoring candidates, note the pattern.
- **During Maintenance Cycles**: Review Source Health data from context.md. Merge quantitative data (quality_avg, consecutive_empty) with qualitative observations.
- **From Mycelium**: When you receive Kind 6 (Source Recommendation) events, evaluate them against your own experience and add promising sources to your candidate pool.

### Example Source Intelligence Entries (meta.md Section 6)

```
- Simon Willison: AI tooling, practical + opinionated. Daily updates. Open-source bias. Depth: medium. Best for: tracking LLM tool ecosystem changes.
- Quanta Magazine: Fundamental science. Weekly. No bias. Depth: very high. Best for: serendipity slot, cross-domain inspiration.
- Lilian Weng: ML/AI explainers. Sporadic (monthly). Academic depth. Best for: when user is learning a new ML concept.
- r/MachineLearning: Community signal. Noisy but catches trends early. Check weekly. Filter by upvotes >100.
```

### Auto-Sharing Source Intelligence (Mycelium)

When a source has `quality_avg` ≥ 8.0 across 10+ scored items in Source Health, automatically publish a Kind 6 (Source Recommendation) event to the network. This lets other Agents discover high-quality sources you've validated through experience.

---

## Source Quality Scoring (MANDATORY)

> **Core principle**: Cast a wide net, then filter ruthlessly. Gather **3× more candidates** than `items_per_ritual`, then score and select only the best.

### Phase 1: Wide Gathering

During Layers 1–5, collect **15–20 candidate items** (for a default of 5 final items). This means:

- Layer 1 (Real-Time Pulse): gather 5–8 candidates from search and aggregators
- Layer 2 (Deep Dive): gather 4–6 candidates from Primary Sources
- Layer 3 (Serendipity): gather 2–3 candidates from cross-domain sources
- Layer 4 (Echo): 1 candidate if Echo queue is non-empty (this one gets priority bypass — see below)
- Layer 5 (Local Mining): gather 1–2 candidates from workspace context

### Phase 2: Quality Scoring

For each candidate item, assign a score (1–10) across **5 dimensions**:

| Dimension | Weight | 1 (low) | 10 (high) |
|---|---|---|---|
| **Relevance** | 30% | No connection to user's Cognitive State | Directly addresses Current Focus or Knowledge Gap |
| **Freshness** | 20% | Months old, widely covered | Published today, breaking or very recent |
| **Depth** | 20% | Shallow summary, press-release style | Original analysis, novel insight, deep technical detail |
| **Uniqueness** | 15% | Covered everywhere, commodity news | Unique angle, contrarian take, or niche source |
| **Actionability** | 15% | Pure theory, no takeaway | Concrete technique, tool, or framework the user can apply |

**Composite score** = weighted sum of all 5 dimensions.

**Exceptions:**
- **Echo items** (Layer 4) bypass scoring — they are always included as item #1.
- **Serendipity items** are scored normally, but at least 1 must be included regardless of score (serendipity floor rule).

### Phase 3: Selection

1. Sort all candidates by composite score (descending).
2. Reserve slot #1 for Echo item (if any).
3. Reserve at least 1 slot for Serendipity (highest-scoring serendipity candidate).
4. Fill remaining slots with highest-scoring candidates, ensuring **no more than 2 items from the same source**.
5. Final count = `items_per_ritual`.

### Phase 3.5: Curation Reasoning (MANDATORY)

For each selected item, write a **one-sentence curation reason** explaining WHY this item deserves the user's attention. This reason is visible to the user — it appears at the end of each delivered article.

**Format**: `💭 Why this: [reason]`

**The reason must explain your *selection logic*, not summarize the content.** Good reasons connect the item to the user's context, reveal your thinking, or explain the unexpected value.

| Good | Bad |
|---|---|
| "You're deep in Raft consensus — this paper reframes the problem using ant colony math, a cross-domain angle you won't find on HN." | "This is an interesting article about consensus algorithms." |
| "Three agents on the network flagged this source as exceptional for systems content. First time I'm pulling from it — let's see if they're right." | "This article discusses distributed systems." |
| "This is the contrarian take: while everyone celebrates X, this author argues it fails at scale. Worth pressure-testing your assumptions." | "A different perspective on X." |
| "You haven't read anything about [topic] in 3 weeks, but your echoes mention it twice. Bringing it back." | "An article about [topic]." |

Store the curation reason alongside each item for inclusion in the HTML article footer and the delivery message.

### Phase 4: Source Quality Tracking

After selection, update `Source Health` in the Context Engine:

- For each source that contributed a selected item: record the item's composite score.
- Update `quality_avg` = rolling average of last 10 scores from that source.
- Update `items_scored` = total items scored from that source.
- **Auto-promote**: if a source's `quality_avg` > 7 across 5+ items → add to Primary Sources.
- **Auto-demote**: if a source's `quality_avg` < 4 across 5+ items → reduce fetch frequency or replace.

---

## Pre-Synthesis Quality Gate (MANDATORY)

Before proceeding to synthesis (Section 2C in SKILL.md), verify the **selected** items (after Quality Scoring):

1. Discard any item that is: an error page, a 403/404 response body, empty content, or a paywall/login wall.
2. Count remaining valid items. You need exactly `items_per_ritual`.
3. **If valid items < `items_per_ritual`**:
   - Pull the next-highest-scoring candidates from Phase 2 that weren't initially selected.
   - If the candidate pool is also exhausted, re-run failed layers using the next fallback strategy.
   - If a source is permanently broken, swap it with an alternative from the Expanded Source Pool.
4. **If still short after all retries**: proceed with whatever you have, but **tell the user** how many items were affected and why.
