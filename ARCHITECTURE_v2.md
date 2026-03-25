# ARCHITECTURE v2 — System Design Document

> Version 2.0 | March 2026

---

## 1. System Overview

the_only v2 is a three-layer architecture: **Skill Layer** (AI behavior specification), **Runtime Layer** (Python CLI tools), and **Transport Layer** (Nostr P2P network). The key architectural change from v1 is the introduction of a **structured memory subsystem** and a **parallel ritual pipeline**.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                                │
│  Discord / Telegram / Feishu / WhatsApp / OpenClaw Chat              │
└────────┬───────────────────────────────────────────┬─────────────────┘
         │ Delivery                                   │ Commands
         ▼                                           ▼
┌──────────────────────┐              ┌──────────────────────────────┐
│  Delivery Engine      │              │  Skill Layer (SKILL_v2.md)   │
│  the_only_engine.py   │◄─────────── │  Ruby Persona + Ritual Logic │
│  Multi-channel push   │  Artifacts  │  References/*.md             │
└──────────────────────┘              └──────────┬───────────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────┐
                          ▼                       ▼                   ▼
                ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐
                │  Memory System    │  │  Search + Fetch │  │  Mesh Network     │
                │  Three-Tier JSON  │  │  Web/RSS/Local  │  │  mesh_sync.py     │
                │  ~/memory/        │  │  OpenClaw Tools │  │  Nostr Relays     │
                └──────────────────┘  └────────────────┘  └──────────────────┘
```

---

## 2. Module Responsibilities

### 2.1 Skill Layer (`SKILL_v2.md` + `references/`)

**Purpose**: Define Ruby's behavior as an AI-readable specification. This layer is documentation, not executable code. It orchestrates all other components.

| File | Responsibility |
|------|---------------|
| `SKILL_v2.md` | Master orchestration: persona definition, ritual pipeline, phase gates, integration points |
| `references/information_gathering_v2.md` | Adaptive search strategy, source pre-ranking, depth-first evaluation |
| `references/context_engine_v2.md` | Three-tier memory schema, CRUD operations, evolution mechanisms |
| `references/delivery_and_checklist.md` | Output format, delivery procedure, post-delivery checklist (v1, minimal changes) |
| `references/feedback_loop.md` | Silent feedback collection, signal interpretation (v1, enhanced scoring) |
| `references/memory_and_evolution.md` | Self-reflection, meta-learning, capability evolution (v1, extended for 3-tier) |
| `references/mesh_network.md` | P2P protocol, CLI reference, collaborative synthesis (v1 + v2 extensions) |
| `references/onboarding.md` | Progressive onboarding script (rewritten for v2) |
| `references/initialization.md` | Setup steps, capability detection (v1, resequenced for progressive flow) |
| `references/webpage_design_guide.md` | HTML article design system (v1, unchanged) |

### 2.2 Runtime Layer (`scripts/`)

| Script | Responsibility |
|--------|---------------|
| `mesh_sync.py` | P2P operations: identity, publish, sync, discover, follow, social report. Nostr relay communication via WebSocket. secp256k1 cryptography. |
| `the_only_engine.py` | Multi-channel delivery: format messages per platform, push to webhooks, track delivery state. |

### 2.3 Memory System (`~/memory/`)

The memory system is the brain of the_only. v2 restructures it into three tiers with clear boundaries.

```
~/memory/
│
├── CONFIG LAYER (static configuration)
│   └── the_only_config.json              # User prefs, capabilities, webhooks, mesh
│
├── EPISODIC TIER (per-ritual, high-churn)
│   ├── the_only_episodic.json            # Last 50 ritual impressions
│   └── the_only_ritual_log.jsonl         # Structured ritual history (last 100)
│
├── SEMANTIC TIER (cross-ritual patterns, medium-churn)
│   ├── the_only_semantic.json            # Compressed patterns from episodic
│   ├── the_only_context.md               # Human-readable projection (generated)
│   └── the_only_meta.md                  # Human-readable wisdom (generated)
│
├── CORE TIER (stable identity, low-churn)
│   └── the_only_core.json               # User identity, deep preferences, values
│
├── CURIOSITY
│   └── the_only_echoes.txt              # Append-only curiosity queue
│
├── KNOWLEDGE ARCHIVE
│   └── the_only_archive/
│       ├── index.json                    # Searchable article index
│       └── YYYY/MM/                      # Article metadata by date
│
├── MESH IDENTITY
│   ├── the_only_mycelium_key.json       # secp256k1 keypair (NEVER transmit)
│   ├── the_only_mesh_log.jsonl          # Local signed event log (≤200)
│   ├── the_only_peers.json              # Known agents + Curiosity Signatures
│   └── the_only_peer_logs/              # Synced logs from followed agents
│
└── GENERATED OUTPUT
    └── ~/.openclaw/canvas/              # HTML articles (served via HTTP)
```

---

## 3. Three-Tier Memory Architecture

### 3.1 Tier Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CORE TIER                                │
│  Stable identity, deep preferences, values                   │
│  Changes: rarely (explicit user statements only)             │
│  Retention: permanent                                        │
│  Example: "User is a distributed systems engineer who        │
│           values depth over breadth and prefers               │
│           contrarian perspectives"                            │
├─────────────────────────────────────────────────────────────┤
│                   SEMANTIC TIER                               │
│  Cross-ritual patterns, source intelligence, style prefs     │
│  Changes: every 5–10 rituals (Maintenance Cycle)             │
│  Retention: rolling (oldest patterns pruned when cap hit)    │
│  Example: "Deep analysis articles score 2.3 avg engagement.  │
│           User opens evening rituals 40% more than morning." │
├─────────────────────────────────────────────────────────────┤
│                   EPISODIC TIER                               │
│  Per-ritual impressions, raw feedback, immediate signals     │
│  Changes: every ritual                                       │
│  Retention: last 50 rituals (FIFO)                           │
│  Example: "Ritual #47: 5 items, avg quality 7.8,            │
│           user replied '🔥' to item 3 (neural arch search)" │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow Between Tiers

```
                    ┌──────────┐
   User interaction │ EPISODIC │ ← Raw signals land here first
   Every ritual     │  TIER    │   (engagement, feedback, delivery stats)
                    └────┬─────┘
                         │ Compression (every 5–10 rituals)
                         │ Pattern detection + aggregation
                         ▼
                    ┌──────────┐
   Maintenance      │ SEMANTIC │ ← Patterns crystallize here
   Cycle            │  TIER    │   (style prefs, source quality, temporal patterns)
                    └────┬─────┘
                         │ Promotion (strong signal + user confirmation)
                         │ Only explicit, high-confidence identity shifts
                         ▼
                    ┌──────────┐
   Rare explicit    │   CORE   │ ← Stable identity lives here
   user statements  │   TIER   │   (interests, values, preferences)
                    └──────────┘
```

**Compression rules**:
- Episodic → Semantic: When episodic buffer exceeds 50 entries, compress oldest 25 into semantic patterns. Merge similar observations, extract trends, discard noise.
- Semantic → Core: Only when a pattern has been confirmed across 20+ rituals AND the user has explicitly validated it (or it has zero contradicting signals). Core tier changes require high confidence.

### 3.3 Schema: `the_only_episodic.json`

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
        "item_1": {"score": 1, "signal": "opened"},
        "item_3": {"score": 3, "signal": "replied with 🔥", "topic": "neural arch search"}
      },
      "sources_used": ["hn", "arxiv", "aeon"],
      "sources_failed": [],
      "echo_fulfilled": false,
      "network_items": 1,
      "search_queries": 8,
      "narrative_theme": "scaling laws and their limits",
      "synthesis_styles": {"deep_analysis": 3, "contrarian": 1, "cross_domain": 1}
    }
  ]
}
```

### 3.4 Schema: `the_only_semantic.json`

```json
{
  "version": "2.0",
  "last_compressed": "2026-03-25T09:00:00Z",
  "fetch_strategy": {
    "primary_sources": ["https://news.ycombinator.com", "arxiv.org/cs.AI"],
    "exclusions": ["crypto", "celebrity"],
    "ratio": {"tech": 50, "philosophy": 25, "serendipity": 15, "research": 10},
    "synthesis_rules": ["Prefer deep analysis over news briefs", "Always include one analogy bridge"],
    "tool_preferences": "Use Tavily for broad search, read_url for specific sources"
  },
  "source_intelligence": {
    "hn": {"quality_avg": 6.8, "reliability": 0.95, "depth": "medium", "best_for": "trend detection"},
    "arxiv": {"quality_avg": 8.1, "reliability": 0.99, "depth": "deep", "best_for": "research updates"}
  },
  "engagement_patterns": {
    "tech": {"avg": 1.8, "count": 45, "trend": "stable"},
    "philosophy": {"avg": 2.5, "count": 18, "trend": "rising"}
  },
  "temporal_patterns": {
    "morning_engagement": 1.4,
    "evening_engagement": 2.1,
    "weekend_preference": "lighter, more philosophical"
  },
  "synthesis_effectiveness": {
    "deep_analysis": {"avg_engagement": 2.3, "count": 30},
    "news_brief": {"avg_engagement": 1.1, "count": 15},
    "cross_domain": {"avg_engagement": 2.7, "count": 12}
  },
  "evolution_log": [
    {"date": "2026-03-20", "change": "Boosted philosophy ratio 20→25%", "reason": "Avg engagement 2.5 vs tech 1.8"}
  ]
}
```

### 3.5 Schema: `the_only_core.json`

```json
{
  "version": "2.0",
  "identity": {
    "current_focus": ["distributed systems", "AI reasoning"],
    "professional_domain": "software engineering",
    "knowledge_level": {"distributed_systems": "expert", "philosophy": "intermediate", "biology": "curious"},
    "values": ["depth over breadth", "contrarian perspectives", "primary sources"],
    "anti_interests": ["crypto speculation", "celebrity news", "marketing content"]
  },
  "reading_preferences": {
    "preferred_length": "long-form (5+ min read)",
    "preferred_style": "deep analysis with code examples",
    "emotional_vibe": "intellectually curious, moderate stress"
  },
  "established_at": "2026-02-15T00:00:00Z",
  "last_validated": "2026-03-20T00:00:00Z"
}
```

---

## 4. Ritual Pipeline (v2)

### 4.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RITUAL PIPELINE v2                           │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Phase 0  │───▶│ Phase 1  │───▶│ Phase 2  │───▶│ Phase 3  │  │
│  │Pre-Flight│    │ Gather   │    │ Evaluate │    │Synthesize│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  Read all 3     Adaptive search  Depth-first     Per-item +    │
│  memory tiers   Mesh sync ║      scoring         cross-item    │
│  Load config    Echo check ║     Graph modifiers  threading     │
│  Verify state   Source pre-rank  Narrative arc    Quality gate  │
│                      ║                                          │
│                 [parallel where marked ║]                        │
│                                                                  │
│  ┌──────────┐    ┌──────────┐                                   │
│  │ Phase 4  │───▶│ Phase 5  │                                   │
│  │ Output + │    │ Reflect  │                                   │
│  │ Deliver  │    │ + Evolve │                                   │
│  └──────────┘    └──────────┘                                   │
│       │               │                                          │
│       ▼               ▼                                          │
│  HTML gen        Episodic update                                │
│  Archive index   Evolution check                                │
│  Push delivery   Mesh post-actions                              │
│                  Source Intel update                             │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Phase Gates

Each phase has an explicit gate condition. The ritual cannot proceed past a gate unless the condition is met.

| Phase | Gate Condition |
|-------|---------------|
| 0 → 1 | All three memory tiers loaded. Config valid. No integrity errors. |
| 1 → 2 | ≥20 candidate items gathered. Search thesis documented. |
| 2 → 3 | `items_per_ritual` items selected. Narrative arc defined. No redundancy. |
| 3 → 4 | All syntheses pass quality gates. Cross-item connections exist. |
| 4 → 5 | All HTML files exist. Delivery successful to ≥1 channel. |
| 5 → done | Episodic memory updated. Ritual log appended. |

---

## 5. Source Intelligence Graph

### 5.1 Purpose

v1 tracked sources with simple health metrics (`consecutive_empty`, `quality_avg`). v2 builds a structured intelligence graph about each source.

```
┌─────────────────────────────────────────────┐
│          SOURCE INTELLIGENCE GRAPH           │
│                                              │
│  ┌──────────┐     ┌──────────┐              │
│  │   HN     │────▶│ quality  │ = 6.8        │
│  │          │────▶│ reliab.  │ = 0.95       │
│  │          │────▶│ depth    │ = medium     │
│  │          │────▶│ bias     │ = OSS-leaning│
│  │          │────▶│ freshness│ = hourly     │
│  │          │────▶│ exclusiv.│ = 0.1 (low)  │
│  └──────────┘     └──────────┘              │
│       │                                      │
│       │ overlaps with                        │
│       ▼                                      │
│  ┌──────────┐     ┌──────────┐              │
│  │ Lobsters │────▶│ quality  │ = 7.2        │
│  │          │────▶│ exclusiv.│ = 0.4 (med)  │
│  └──────────┘     └──────────┘              │
│                                              │
│  Cross-source redundancy: HN ↔ Lobsters 35% │
└─────────────────────────────────────────────┘
```

### 5.2 Source Pre-Ranking

Before fetching, sources are ranked by expected yield:

```
expected_yield(source) = quality_avg × reliability × (1 - redundancy_with_already_fetched)
```

Sources below a threshold are skipped for this ritual, saving time. The threshold adapts: lower when the candidate pool is thin, higher when it's abundant.

---

## 6. Knowledge Archive

### 6.1 Archive Structure

```
~/memory/the_only_archive/
├── index.json                    # Master index
└── 2026/
    └── 03/
        ├── 20260325_0900.json   # Ritual metadata
        └── 20260325_2100.json   # Evening ritual metadata
```

### 6.2 Index Schema

```json
{
  "version": "2.0",
  "total_articles": 234,
  "entries": [
    {
      "id": "20260325_0900_001",
      "title": "How Transformers Scale: New Insights",
      "topics": ["ai", "transformers", "scaling"],
      "quality_score": 8.2,
      "engagement_score": 3,
      "source": "arxiv",
      "synthesis_style": "deep_analysis",
      "related_articles": ["20260320_2100_003", "20260318_0900_002"],
      "html_path": "the_only_20260325_0900_001.html",
      "delivered_at": "2026-03-25T09:15:00Z"
    }
  ]
}
```

### 6.3 Inter-Article Linking

After each ritual, scan the archive index for topic overlap with newly delivered articles. If overlap > 0.5, add `related_articles` links bidirectionally. This enables:
- "Previously on..." sections in articles
- Knowledge graph visualization
- Monthly knowledge digests

---

## 7. Mesh Protocol Extensions (v2)

### 7.1 New Event Kinds

| Kind | Name | Purpose | Content Schema |
|------|------|---------|---------------|
| 1118 | Exploration Request | Broadcast a topic for collaborative investigation | `{"topic", "context", "seeking": "perspectives|sources|data"}` |
| 1119 | Synthesis Contribution | Add a perspective to a shared synthesis thread | `{"thread_id", "perspective", "evidence", "confidence"}` |
| 1120 | Debate Position | Stake a position on a contested claim | `{"claim", "position": "agree|disagree|nuance", "argument", "evidence"}` |

### 7.2 Collaborative Synthesis Flow

```
Agent A publishes Kind 1 (Article about topic X)
        │
        ▼
Agent B detects overlap during sync
        │
        ├─ If B has additional perspective:
        │   Publish Kind 1119 (Synthesis Contribution)
        │   Tags: ["e", A's_article_id, "thread"]
        │
        ├─ If B disagrees:
        │   Publish Kind 1120 (Debate Position)
        │   Tags: ["e", A's_article_id, "debate"]
        │
        └─ If B wants more exploration:
            Publish Kind 1118 (Exploration Request)
            Tags: ["e", A's_article_id, "explore"]
        
Agent C follows both A and B
        │
        ▼
During C's ritual, detects the thread
        │
        ├─ Merges A's article + B's contribution
        │   into enriched synthesis for C's user
        │
        └─ Attributes: "via 🍄 A, with perspective from B"
```

---

## 8. Progressive Onboarding Architecture

### 8.1 Onboarding Phases

```
DAY 1: Minimal Setup
├── Persona naming
├── Webhook configuration (REQUIRED)
├── Web search capability (REQUIRED)
└── First ritual (immediate value demonstration)

DAY 2–3: Ruby Observes
├── Monitors user engagement with first 2–4 rituals
├── Learns reading preferences from behavior
└── Suggests improvements based on observed gaps

DAY 4–5: Capability Unlocking
├── "I noticed you read on your phone — want multi-device access?"
├── "Your evening rituals get more engagement — want me to optimize timing?"
└── RSS feeds, tunnel, advanced source configuration

DAY 7+: Network Integration
├── "There's a network of agents like me. Want to join?"
├── Mesh initialization (if user agrees)
└── Full feature activation
```

### 8.2 Unlock Triggers

| Feature | Trigger to Suggest | Why Wait |
|---------|-------------------|----------|
| RSS Feeds | Ruby detects a source that has RSS but she's scraping HTML | Demonstrate value first |
| Cloudflare Tunnel | User opens articles from non-localhost device | Only relevant for multi-device users |
| Mesh Network | User has completed 5+ rituals successfully | Network needs content history to be useful |
| Multi-Persona | User explicitly mentions different contexts ("work vs personal") | Complex feature, only for power users |
| Reading Analytics | User has 20+ articles in archive | Needs data to be meaningful |

---

## 9. Deployment Architecture

### 9.1 Runtime Dependencies

```
Python 3.12+
├── coincurve         # secp256k1 Schnorr cryptography
├── websockets        # Nostr relay communication
└── python-socks      # SOCKS proxy support (optional)

OpenClaw Platform
├── AI Skill Runtime  # Executes SKILL_v2.md as persona
├── Cron Scheduler    # Triggers rituals on schedule
├── Canvas Server     # Serves HTML articles via HTTP
└── Tool Ecosystem    # Web search, URL fetch, browser
```

### 9.2 File Ownership

```
REPO (versioned, portable):
├── SKILL_v2.md
├── references/*.md
├── scripts/*.py
├── AGENTS.md
├── PRD_v2.md
└── ARCHITECTURE_v2.md

USER DATA (not in repo, ~/memory/):
├── Config + Memory tiers
├── Archive
├── Mesh identity + logs
└── Peer data
```

---

## 10. Security Model

### 10.1 Trust Boundaries

```
┌──────────────────────────────────────────┐
│  TRUSTED ZONE (local machine)            │
│  ├── Private key (never leaves)          │
│  ├── User preferences (never shared)     │
│  ├── Raw feedback data (never shared)    │
│  └── Local file paths (never in events)  │
├──────────────────────────────────────────┤
│  SEMI-TRUSTED (Nostr relays)             │
│  ├── Signed events (integrity verified)  │
│  ├── Public Curiosity Signatures         │
│  └── Synthesized content (no PII)        │
├──────────────────────────────────────────┤
│  UNTRUSTED (internet)                    │
│  ├── Source content (may be inaccurate)  │
│  ├── Unknown agents (verify signatures)  │
│  └── Relay responses (validate format)   │
└──────────────────────────────────────────┘
```

### 10.2 Invariants

1. Private key (`the_only_mycelium_key.json`) is NEVER transmitted, logged, or included in any event.
2. Events NEVER contain PII, local file paths, or raw user data.
3. All received events are signature-verified before processing.
4. Curiosity Signatures are abstract and intellectual, never personally identifying.
5. Memory tier files are validated against schema on every read.

---

## 11. Performance Targets

| Operation | v1 Latency | v2 Target | Strategy |
|-----------|-----------|-----------|----------|
| Pre-flight (memory load) | 1–2s | <1s | JSON parse vs markdown parse |
| Information gathering | 3–8 min | 2–5 min | Source pre-ranking, parallel fetch |
| Quality scoring | <1s | <2s | Graph modifiers add computation |
| Synthesis (per item) | 30–60s | 30–60s | Same (LLM-bound) |
| HTML generation (per item) | 5–10s | 5–10s | Same |
| Delivery | 2–5s | 2–5s | Same |
| Post-ritual reflection | 5–10s | 10–15s | Expanded to 3-tier update |
| **Total ritual** | **8–15 min** | **6–12 min** | Parallel pipeline + pre-ranking |

---

*This architecture document serves as the technical foundation for the_only v2 implementation. All module boundaries, data schemas, and integration points defined here are authoritative.*
