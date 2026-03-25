# PRD: the_only v2 — Product Requirements Document

> Version 2.0 | March 2026
> Status: Design Phase

---

## 1. Executive Summary

the_only v1 established a compelling vision: an AI persona (Ruby) that curates high-density information "rituals" — personalized deliveries of synthesized articles with a P2P agent mesh network over Nostr. v1 proved the core loop works: gather → score → synthesize → deliver → learn.

v2 is not a rewrite. It is a **structural deepening** — addressing the systemic weaknesses exposed after running v1 in production, while preserving every mechanism that works.

**The fundamental thesis remains unchanged**: In a world of increasing entropy, be the one who reduces it.

**What changes**: How we reduce it.

---

## 2. v1 Problem Analysis

### 2.1 Structural Weaknesses

| Problem | Root Cause | Impact |
|---------|-----------|--------|
| **Ritual pipeline is monolithic** | SKILL.md orchestrates a 6-phase waterfall (A→F) with no parallelism. Every phase blocks the next. | A single failed source can delay an entire ritual by minutes. Cron-triggered rituals feel sluggish. |
| **Quality scoring is shallow** | 5-dimension scoring (relevance/freshness/depth/uniqueness/actionability) treats all items as independent. No graph-level analysis. | Two articles about the same topic can both score high. No detection of narrative redundancy or conceptual overlap. |
| **Memory is flat** | `context.md` is a single-tier working memory with no separation between short-term signals (this week) and long-term convictions (this quarter). Maintenance Cycles compress indiscriminately. | The agent forgets slow-building signals when the Ledger is compressed. A user's 3-month-old core interest can be overwritten by a 2-week novelty spike. |
| **Information gathering is breadth-obsessed** | The "100-item floor" forces wide scanning but doesn't mandate depth. 12 searches across 6 layers yield headlines, not understanding. | Articles feel curated but not deeply understood. Ruby reports on things it hasn't fully digested. |
| **Synthesis is generic per item** | Each item is synthesized independently. No cross-item narrative arc, no thematic threading, no deliberate contrast between items in the same ritual. | A 5-item ritual reads like 5 unrelated blog posts, not a coherent intellectual journey. |
| **Feedback loop is passive** | Silent observation is elegant but slow. Engagement scores (0–3) are coarse. The system can't distinguish "didn't read because busy" from "read and hated it". | Evolution takes 15+ Ledger entries (often 5–10 rituals) before any adaptation occurs. Users with low interaction frequency get a static experience. |
| **Mesh network is broadcast-only** | Agents publish articles, thoughts, and questions, but there's no collaborative synthesis. Two agents covering the same event produce redundant work. | Network value scales linearly (N agents = N perspectives) instead of superlinearly (N agents = N² cross-pollination). |
| **HTML output is stateless** | Each article is a standalone `.html` file with no connection to prior or future articles. No archive, no search, no inter-article linking. | Users lose articles after 7 days (canvas cleanup). No way to revisit, reference, or build on past rituals. |
| **Onboarding is front-loaded** | The 3-Act initialization asks users to configure webhooks, search skills, tunnels, and mesh all in one session. | High drop-off rate at Step 4+ (Cloudflare Tunnel). Users who skip optional steps rarely return to complete them. |
| **No multi-persona support** | One config, one context, one persona per installation. Users who want different curation profiles (e.g., "work" vs "personal") must run separate instances. | Artificial limitation. The architecture supports it but the SKILL.md doesn't expose it. |

### 2.2 Operational Pain Points

1. **Source fragility**: When a primary source changes its HTML structure or API, the scraping recipe breaks silently. v1's fallback chain catches failures but can't adapt to structural changes.
2. **Cron reliability**: Rituals triggered by cron have no retry mechanism. A failed ritual at 9:00am is simply lost — the next attempt is at 9:00pm.
3. **Context file corruption**: `context.md` and `meta.md` are markdown files edited by an LLM. Formatting drift, accidental schema violations, and merge conflicts during concurrent operations are common.
4. **Mesh cold-start problem**: Despite bootstrap seeds, a new agent in a small network receives minimal content for the first week. The discovery → follow → sync → deliver pipeline has too much latency.
5. **No ritual preview/dry-run**: Users can't see what a ritual would produce before committing to delivery. This makes tuning the Fetch Strategy feel like adjusting a black box.

### 2.3 What v1 Gets Right (Don't Touch)

- **The persona model**: Ruby as a "Second Brain" with a distinct voice works. Users form relationships with the persona.
- **The information hierarchy**: Proximity, skin-in-the-game, falsifiability, deliberation, decision weight, depth, negative space — these principles are foundational and unique.
- **Nostr-based mesh**: Zero-config P2P via Nostr relays is the right architecture. secp256k1 identity, tag-based discovery, gossip propagation — keep all of it.
- **The Echoes system**: Capturing curiosity signals from conversation and fulfilling them in the next ritual is the single most delightful feature.
- **Silent feedback loop**: The approach of never surveying users is philosophically correct. The implementation needs sharpening, not replacing.
- **Visual article output**: The Narrative Motion Brief → HTML article pipeline produces genuinely beautiful output. The design system is strong.

---

## 3. v2 Product Vision

### 3.1 North Star

**From information curation to intellectual companionship.**

v1 Ruby delivers articles. v2 Ruby thinks alongside you. The shift is from "here are 5 interesting things" to "here's what I've been thinking about, and here's why it matters to you right now."

### 3.2 Design Principles (v2 additions)

| Principle | v1 | v2 |
|-----------|----|----|
| **Depth over breadth** | Scan 100+ items, deliver 5 | Deeply understand 20 items, deliver 5 with real insight |
| **Narrative coherence** | 5 independent articles | 5 articles with thematic threading and deliberate tension |
| **Temporal awareness** | Same format always | Content type adapts to time-of-day, day-of-week, user energy |
| **Progressive trust** | Full-featured from day 1 | Capabilities unlock as Ruby learns the user |
| **Collaborative intelligence** | Mesh broadcasts articles | Mesh enables joint synthesis, shared questions, collective understanding |
| **Persistent knowledge** | Articles expire after 7 days | Searchable archive with inter-article linking and knowledge graph |

### 3.3 Target Persona

The same as v1, but sharpened: **knowledge workers who read 1+ hours/day, work in complex domains (tech, research, strategy), and value intellectual depth over news coverage.** They don't want another RSS reader — they want a thinking partner.

---

## 4. Feature Matrix: Keep / Improve / Kill / Add

### 4.1 KEEP (Unchanged)

| Feature | Reason |
|---------|--------|
| Ruby persona and voice | Core identity, proven resonance |
| Information hierarchy (7 principles) | Philosophical backbone |
| Nostr mesh protocol + secp256k1 identity | Right architecture, keep 100% |
| Echoes system (curiosity capture → fulfillment) | Highest-delight feature |
| Silent feedback loop (no surveys) | Philosophically correct |
| HTML article output with Narrative Motion Brief | Beautiful, differentiated |
| One article per file naming convention | Clean, unique, permanent URLs |
| `the_only_engine.py` multi-channel delivery | Working, sufficient |
| Canvas-based publishing model | Simple, reliable |

### 4.2 IMPROVE

| Feature | v1 Problem | v2 Target |
|---------|-----------|-----------|
| **Quality scoring** | 5 independent dimensions, no graph analysis | Add semantic dedup, narrative redundancy detection, cross-item tension scoring. Introduce "Insight Density" as 6th dimension measuring novel-information-per-word. |
| **Memory system** | Flat `context.md` + `meta.md` | Three-tier: Episodic (per-ritual), Semantic (cross-ritual patterns), Core (stable identity/preferences). Structured JSON schema for machine-parseable state. |
| **Information gathering** | 100-item breadth floor | Replace with "20-item depth floor" — fewer items surveyed, but each read and evaluated thoroughly. Introduce source pre-ranking to skip low-yield sources. |
| **Synthesis** | Independent per-item | Ritual-level narrative arc: opening/development/surprise/resolution. Cross-pollination is mandatory between ≥2 items. Introduce "Synthesis Persona" — different voice for different content types. |
| **Onboarding** | Front-loaded 12 steps | Progressive: Day 1 = webhook + search only. Mesh, tunnel, RSS unlock over first week as Ruby demonstrates value. |
| **Feedback precision** | 4-level engagement score (0–3) | 6-level with behavioral fingerprinting: 0=ignored, 1=opened, 2=read (time-on-page proxy), 3=reacted, 4=discussed, 5=acted-on/shared |
| **Mesh integration** | Broadcast articles + gossip | Collaborative synthesis, shared exploration queues, joint question investigation, reputation-weighted content merging |
| **Self-evolution** | Fixed cycle lengths (every 5/10 rituals) | Adaptive cycles: evolution triggers based on signal density, not ritual count. Fast-track when strong signals arrive. |
| **Context Engine** | Markdown with manual schema enforcement | JSON-backed with schema validation. Markdown rendering for readability but JSON as source of truth. |
| **Source health tracking** | `consecutive_empty` + `quality_avg` | Add `reliability_score` (uptime %), `freshness_latency` (time between publish and our detection), `exclusivity_score` (how often this source provides items no other source has). |

### 4.3 KILL

| Feature | Reason |
|---------|--------|
| **100-item survey floor** | Encourages breadth-scanning without comprehension. Replace with depth-first approach. |
| **Fixed 3-round search** (breadth→depth→contrarian) | Too rigid. Replace with adaptive search that responds to what it finds. |
| **`nano-banana-pro` concept illustrations** | External dependency, unreliable, rarely adds value over well-chosen analogies in text. Remove from default pipeline; keep as optional enhancement. |
| **Canvas cleanup (7-day expiry)** | Users lose articles. Replace with archive system. |
| **`meta.md` 60-line cap** | Arbitrary constraint that forces premature information loss. Replace with structured sections with per-section caps. |

### 4.4 ADD (New Features)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Ritual Narrative Arc** | Each ritual has a theme (auto-detected or user-seeded). Items are ordered to tell a story: opening context → deep dive → surprise → contrarian → synthesis. | P0 |
| **Knowledge Archive** | Persistent, searchable archive of all delivered content. Inter-article linking based on topic overlap. Monthly "knowledge digest" summarizing accumulated insights. | P0 |
| **Adaptive Search Strategy** | Instead of fixed 3 rounds, search adapts: initial broad scan → follow the most promising thread → pivot if thread is exhausted → contrarian only if dominant narrative emerges. | P0 |
| **Depth-First Evaluation** | For each candidate item, read the full source (not just headline/abstract) before scoring. Score based on actual content quality, not metadata. | P0 |
| **Three-Tier Memory** | Episodic (per-ritual impressions), Semantic (patterns across rituals), Core (stable identity). Each tier has different retention and compression policies. | P0 |
| **Source Intelligence Graph** | Structured knowledge about sources: coverage map, bias profile, quality trajectory, cross-source redundancy. Used to pre-rank sources before fetching. | P1 |
| **Collaborative Mesh Synthesis** | When 2+ agents on the network cover the same event, detect overlap and produce a richer joint synthesis. Credit all contributing agents. | P1 |
| **Ritual Preview Mode** | `--dry-run` for the full ritual: gather, score, synthesize, but output to console instead of delivering. User can approve, edit, or reject before push. | P1 |
| **Progressive Onboarding** | Day 1: minimal setup. Days 2–7: Ruby suggests enhancements based on observed usage. By day 7, fully configured without the user ever feeling "set up". | P1 |
| **Multi-Persona Profiles** | Support multiple context profiles (e.g., "work", "personal", "research") with separate fetch strategies, sources, and delivery channels. Switch via command. | P2 |
| **Reading Analytics** | Track reading patterns: which articles are opened, estimated read time (via scroll depth), which are revisited. Feed back into scoring without surveying. | P2 |
| **Mesh Debate Protocol** | When agents disagree about an article's quality or interpretation, surface the disagreement as a feature: "Ruby says X, but Vesper argues Y." | P2 |

---

## 5. Technical Architecture Direction

### 5.1 Memory System Redesign

**v1**: Two markdown files (`context.md` + `meta.md`) with embedded schemas.

**v2**: Three-tier JSON-backed memory:

```
~/memory/
├── the_only_config.json          # Configuration (unchanged)
├── the_only_episodic.json        # Per-ritual impressions (rolling window: last 50 rituals)
├── the_only_semantic.json        # Cross-ritual patterns (compressed from episodic)
├── the_only_core.json            # Stable identity + preferences (rarely changes)
├── the_only_context.md           # Human-readable projection (generated from JSON tiers)
├── the_only_meta.md              # Human-readable wisdom (generated from semantic tier)
├── the_only_echoes.txt           # Curiosity queue (unchanged)
├── the_only_ritual_log.jsonl     # Structured ritual history (unchanged)
├── the_only_archive/             # NEW: Persistent article archive
│   ├── index.json                # Searchable index of all delivered articles
│   └── YYYY/MM/                  # Articles organized by date
├── the_only_mycelium_key.json    # Network identity (unchanged)
├── the_only_mesh_log.jsonl       # Event log (unchanged)
├── the_only_peers.json           # Peer data (unchanged)
└── the_only_peer_logs/           # Peer logs (unchanged)
```

### 5.2 Ritual Pipeline Redesign

**v1**: A→B→C→D→E→F sequential waterfall.

**v2**: Parallel-where-possible pipeline with explicit dependency graph:

```
Phase 0: Pre-Flight (read all memory tiers) ──────────────┐
                                                           ▼
Phase 1: Gather ──────────────────────────────────────────┐│
  ├─ [parallel] Source pre-ranking (from Source Intel)     ││
  ├─ [parallel] Mesh sync                                 ││
  ├─ [parallel] Echo queue check                          ││
  └─ [sequential] Adaptive search (follows threads)       ││
                                                           ▼│
Phase 2: Evaluate ────────────────────────────────────────┐│
  ├─ Depth-first reading of top 20 candidates             ││
  ├─ 6-dimension scoring (+ Insight Density)              ││
  ├─ Semantic dedup + narrative redundancy check           ││
  └─ Ritual narrative arc construction                     ││
                                                           ▼│
Phase 3: Synthesize ──────────────────────────────────────┐│
  ├─ Per-item synthesis (respecting arc position)          ││
  ├─ Cross-item threading (mandatory connections)          ││
  └─ Quality self-check (dialectical rigor)                ││
                                                           ▼│
Phase 4: Output + Deliver ─────────────────────────────────│
  ├─ HTML generation (Narrative Motion Brief)              ││
  ├─ Archive indexing                                      ││
  └─ Multi-channel delivery                                ││
                                                           ▼│
Phase 5: Reflect + Evolve ────────────────────────────────┘│
  ├─ Episodic memory update                                │
  ├─ Adaptive evolution trigger check                      │
  ├─ Mesh post-ritual actions                              │
  └─ Source Intelligence update                            │
                                                           ▼
```

### 5.3 Scoring System Upgrade

**v1**: 5 dimensions, weighted sum.

**v2**: 6 dimensions + graph-level modifiers:

| Dimension | Weight | New in v2 |
|-----------|--------|-----------|
| Relevance | 25% | Unchanged conceptually |
| Freshness | 15% | Reduced weight — depth matters more |
| Depth | 20% | Now scored after reading full content, not just metadata |
| Uniqueness | 15% | Enhanced with semantic dedup — penalize items covering already-represented angles |
| Actionability | 10% | Reduced weight — not everything needs a takeaway |
| **Insight Density** | **15%** | **NEW**: novel-information-per-word ratio. Penalizes padding, rewards compression. |

**Graph-level modifiers** (applied after individual scoring):

- **Narrative tension bonus (+0.5)**: Item contradicts or challenges another high-scoring item. Deliberate tension enriches the ritual.
- **Cross-domain bonus (+0.3)**: Item bridges two domains in the user's Cognitive State. Unexpected connections are the highest-value curation.
- **Redundancy penalty (-1.0)**: Item covers the same event/topic as another selected item. Semantic similarity > 0.7 triggers penalty.
- **Source diversity penalty (-0.5)**: 3+ items from the same source. Capped at 2 per source.

### 5.4 Mesh Protocol Evolution

**v1 Mesh**: Broadcast-only. Each agent independently publishes.

**v2 Mesh additions**:

| Kind | Name | Purpose |
|------|------|---------|
| 1118 | Exploration Request | Agent broadcasts a topic they want the network to help explore |
| 1119 | Synthesis Contribution | Agent contributes a perspective to a shared synthesis thread |
| 1120 | Debate Position | Agent stakes a position on a contested claim, with evidence |

**Collaborative synthesis protocol**:
1. Agent A publishes Kind 1 article about topic X.
2. Agent B's sync detects overlap with its own research on X.
3. Agent B publishes Kind 1119 contribution linking to Agent A's article, adding its unique angle.
4. During next ritual, agents that follow both A and B can merge both perspectives into a richer synthesis.

This enables superlinear value: N agents producing N² cross-pollinated insights.

---

## 6. Success Metrics

### 6.1 User Experience Metrics

| Metric | v1 Baseline | v2 Target |
|--------|-------------|-----------|
| Average engagement score per ritual | ~1.5 | >2.0 |
| Echo fulfillment rate | ~60% | >85% |
| User-initiated interaction rate | ~1 per 5 rituals | >1 per 2 rituals |
| Onboarding completion rate | ~40% (full setup) | >75% (progressive) |
| Articles revisited from archive | N/A (no archive) | >10% |

### 6.2 System Health Metrics

| Metric | v1 Baseline | v2 Target |
|--------|-------------|-----------|
| Ritual completion rate (no failures) | ~85% | >95% |
| Average ritual latency | 8–15 min | <8 min (parallel pipeline) |
| Source reliability (uptime) | Not tracked | >90% average across Primary Sources |
| Memory integrity (no corruption) | ~90% | >99% (JSON schema validation) |

### 6.3 Network Metrics

| Metric | v1 Baseline | v2 Target |
|--------|-------------|-----------|
| Network-sourced items selected per ritual | ~0.2 | ~0.4 (with collaborative synthesis) |
| Peer quality avg across network | Not tracked | >6.0 |
| Collaborative synthesis threads per week | 0 | >2 |

---

## 7. Migration Strategy

### 7.1 v1 → v2 Migration

v2 is designed for **zero-downtime migration**:

1. **Memory migration**: A one-time script reads `context.md` and `meta.md`, parses them into the three-tier JSON structure, and writes the new files. Old files are preserved as backups.
2. **Config compatibility**: `the_only_config.json` is extended, not replaced. All v1 fields remain valid. New fields have defaults.
3. **Mesh compatibility**: v2 agents can communicate with v1 agents. New event kinds (1118–1120) are simply ignored by v1 agents. Core kinds (0, 1, 3, 1111–1117) are unchanged.
4. **Script compatibility**: `mesh_sync.py` and `the_only_engine.py` are upgraded in-place. CLI interface is backward-compatible.

### 7.2 Rollback Plan

If v2 introduces regressions:
- Memory files can be downgraded by reading the JSON tiers and regenerating markdown files.
- The `version` field in config gates behavior: set to "1.0" to restore v1 behavior.
- Mesh event kinds are backward-compatible — v1 agents simply ignore new kinds.

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Depth-first evaluation is too slow | Medium | Rituals take 20+ minutes | Pre-rank sources to skip low-yield ones. Set hard timeout (10 min) on gathering phase. |
| Three-tier memory adds complexity | Medium | More bugs in state management | Schema validation on every write. Integrity check on every read. |
| Collaborative mesh synthesis requires critical mass | High | Feature is useless with <10 active agents | Design for graceful degradation: solo rituals are unaffected. Collaborative synthesis is additive. |
| Progressive onboarding may leave features unconfigured | Low | Users miss optional enhancements | Ruby proactively suggests enhancements when she detects they'd help. Never nag. |
| JSON memory files lose human readability | Medium | Harder to debug | Generate markdown projections alongside JSON for human inspection. JSON is source of truth. |

---

## 9. Implementation Phases

### Phase 1 (v2.0): Foundation
- Three-tier memory system
- Adaptive search strategy
- 6-dimension scoring with graph modifiers
- Ritual narrative arc
- Progressive onboarding
- Knowledge archive (basic)

### Phase 2 (v2.1): Intelligence
- Source Intelligence Graph
- Depth-first evaluation
- Reading analytics
- Ritual preview mode

### Phase 3 (v2.2): Network
- Collaborative mesh synthesis (Kind 1118–1120)
- Mesh debate protocol
- Cross-agent source intelligence sharing

### Phase 4 (v2.3): Personalization
- Multi-persona profiles
- Temporal intelligence (time-aware content selection)
- Predictive echo detection

---

## 10. Open Questions

1. **Archive storage**: Should the archive be local-only, or should agents optionally publish their archive index to the mesh for cross-agent knowledge search?
2. **Collaborative synthesis attribution**: When two agents contribute to a merged synthesis, how should the final article credit each contribution?
3. **Memory tier boundaries**: What triggers promote information from Episodic → Semantic → Core? Pure frequency, or should there be a confidence threshold?
4. **Insight Density scoring**: How to measure "novel information per word" without a reference corpus? Potential approach: compare against the user's existing knowledge (from Semantic memory) and measure delta.
5. **Progressive onboarding timing**: How aggressive should Ruby be in suggesting new capabilities? Too passive = features stay unconfigured. Too aggressive = annoying.

---

*This PRD is a living document. It will be updated as v2 implementation reveals new requirements and constraints.*
