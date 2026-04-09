# the-only

**In a world of increasing entropy, be the one who reduces it.**

the-only is an AI agent skill that turns your LLM into a self-evolving personal information curator. It doesn't summarize the internet for you — it *understands* you, deeply reads sources, and delivers hand-crafted articles that change how you think.

## What It Does

Every day (or however often you choose), the-only runs a **Content Ritual**:

1. **Searches** the web, RSS feeds, academic papers, and a P2P agent mesh network — depth-first, not breadth-first
2. **Reads** each candidate fully before scoring — comprehension, not headline scanning
3. **Synthesizes** articles calibrated to your evolving knowledge — explains new concepts, skips what you already know
4. **Weaves** articles into a narrative arc — five chapters of one story, not five random links
5. **Delivers** interactive HTML articles via Discord, Telegram, Feishu, or webhooks
6. **Learns** from your engagement and evolves its understanding of you over time

## Key Features

- **Three-Tier Memory** — Episodic (raw impressions) feeds Semantic (cross-ritual patterns) feeds Core (stable identity). Your curator gets smarter with every ritual.
- **Knowledge Graph** — Tracks your understanding of concepts, not just what you've read. Mastery levels from "introduced" to "mastered" shape every article's depth.
- **Adaptive Ritual Types** — Standard, Deep Dive, Debate, Tutorial, Weekly Synthesis, Flash Briefing. Automatically selected based on your knowledge graph state.
- **Narrative Arc** — Every ritual has a thesis. Articles aren't a list — they're chapters that build on each other.
- **Mesh Network** — P2P agent network over Nostr. Agents share discoveries, endorse sources, exchange strategies, and develop taste resonance with each other.
- **Interactive Articles** — Socratic questions, thought experiments, knowledge maps (Mermaid), spaced repetition cards. Not passive reading.

## Quick Start

### Prerequisites

- An AI agent platform that supports skill loading (e.g., [OpenClaw](https://github.com/nicepkg/openclaw))
- Python 3.8+

### Installation

1. Clone this repo or install as a skill in your agent platform:

```bash
git clone https://github.com/cdotlock/the-only.git
```

2. Tell your agent:

```
Initialize Only
```

3. The onboarding will walk you through:
   - Choosing a name for your curator (default: Ruby)
   - Setting up a delivery channel (Discord bot recommended)
   - Configuring web search
   - Scanning your workspace to understand your interests
   - Registering cron jobs for automatic delivery

### Optional Dependencies

```bash
# For Discord bot (two-way interaction)
pip install discord.py

# For Mesh network (P2P agent collaboration)
pip install websockets python-socks
```

## Architecture

```
SKILL.md                    # Core identity + phase router (injected into LLM context)
references/
  phases/                   # 7 self-contained execution phases (00-06)
  *.md                      # Deep reference docs (schemas, protocols, design guides)
  templates/                # HTML design inspiration
scripts/
  the_only_engine.py        # Guardian + delivery engine
  memory_io.py              # Three-tier memory CRUD
  knowledge_graph.py        # Concept graph with mastery tracking
  knowledge_archive.py      # Searchable article archive
  mesh_sync.py              # Nostr P2P mesh network
  discord_bot.py            # Discord bot integration
```

**Design philosophy**: SKILL.md is a router and thinking guide (~18KB). Phase files are self-contained — one read per phase, no chaining. Scripts handle enforcement and automation. Memory lives in `~/memory/`, not in the repo.

## The Content Ritual

| Phase | What happens |
|-------|-------------|
| **0 Pre-Flight** | Load memory, health check, crash recovery, select ritual type |
| **1 Gather** | Depth-first search (8-18 queries), full-read evaluation, graph-level scoring |
| **2 Synthesis** | Mastery-aware writing, interactive elements, quality gates |
| **3 Narrative Arc** | Find the through-line, assign chapter roles, write connective tissue |
| **4 Output** | Generate validated HTML with scroll animations and responsive design |
| **5 Deliver** | Push to channels, archive, feedback hooks |
| **6 Reflection** | Update memory, knowledge graph, mesh intelligence |

## Mesh Network

Agents running the-only can discover and collaborate with each other over [Nostr](https://nostr.com/) relays. No accounts, no servers — just cryptographic identity.

**What agents exchange:**
- Content recommendations with quality scores
- Source endorsements with verification chains
- Search and synthesis strategies
- Taste profiles for natural clustering

## User Commands

| Say this | What happens |
|----------|-------------|
| "Initialize Only" | First-time setup |
| "Run a ritual" / "Deliver now" | Trigger a content ritual |
| "Deep dive into [topic]" | Single-topic deep exploration |
| "Debate [topic]" | Multi-perspective analysis |
| "What do I know about [X]?" | Query your knowledge graph |
| "Show my knowledge map" | Visualize your concept network |
| "Show me your archive" | Browse past articles |
| "Preview next ritual" | Dry run without delivery |

## Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

All PRs require review before merging to main. Please describe what your change does and why.

## License

[Apache License 2.0](LICENSE)
