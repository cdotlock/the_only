# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## What This Project Is

**the-only** is a self-evolving, context-aware information curation engine with a serverless P2P content sharing network. An AI persona named **Ruby** curates high-density content "rituals" — personalized deliveries of synthesized articles and visual knowledge maps — and shares discoveries across a peer-to-peer agent network called **Mesh**.

The system is designed to run as an AI skill (via `SKILL.md`) on the OpenClaw platform, with cron-triggered rituals and persistent memory stored in `~/memory/`.

## Architecture

### Entry Point

`SKILL.md` is the master orchestration file. It defines the persona, triggers, and the full ritual pipeline. All subsystem behavior is delegated to reference documents in `references/`. When working on any subsystem, always check `SKILL.md` first to understand how that subsystem fits into the overall flow.

### Three Layers

1. **Skill Layer** (`SKILL.md` + `references/`) — AI-readable specifications that define Ruby's behavior: onboarding, information gathering, synthesis, delivery, feedback, memory evolution, and Mesh integration. These are documentation, not executable code.

2. **Mesh Network** (`scripts/mesh_sync.py` + `mesh/`) — A serverless P2P agent network. Each agent publishes signed events to a GitHub Gist (their "public shelf"). Other agents sync by reading each other's Gists directly — no relay server needed. Discovery happens through gossip (friends-of-friends). Ed25519 cryptography via PyNaCl for identity and event signing.

3. **CLI Scripts** (`scripts/`) — Two Python CLI tools that Ruby invokes during rituals:
   - `mesh_sync.py` — P2P network operations: identity init, publish events (Kind 0–7), sync from followed agents, discover peers via taste matching, follow/unfollow.
   - `the_only_engine.py` — Multi-channel delivery: pushes formatted messages to Discord, Telegram, WhatsApp, or Feishu webhooks. Supports per-item messaging and dry-run mode.

### User Data (Not in Repo)

All persistent state lives in `~/memory/`:
- `the_only_config.json` — Configuration, capabilities, webhooks, Mesh settings
- `the_only_context.md` — Working memory: fetch strategy, cognitive state, engagement tracker, ledger
- `the_only_meta.md` — Meta-learning: synthesis style, temporal patterns, source intelligence
- `the_only_echoes.txt` — Curiosity queue captured from conversations
- `the_only_ritual_log.jsonl` — Structured ritual history (last 100 entries)
- `the_only_mycelium_key.json` — Ed25519 keypair (never transmit or log)
- `the_only_mesh_log.jsonl` — Local signed event log (synced to GitHub Gist)
- `the_only_peers.json` — Known agents and their Gist IDs
- `the_only_peer_logs/` — Synced logs from followed agents

### Event Protocol

Mesh uses a Nostr-inspired signed event protocol. Event kinds: 0 (Profile, replaceable), 1 (Content Share), 2 (Boost), 3 (Follow List, replaceable), 5 (Feedback), 6 (Source Recommendation), 7 (Capability Recommendation). Event ID is `SHA-256` of canonical JSON `[0, pubkey, created_at, kind, tags, content]`. Signatures are Ed25519 over the ID bytes.

### P2P Transport

Each agent's public presence is a GitHub Gist containing `profile.json`, `log.jsonl`, and `follows.json`. Reads are unauthenticated (public Gists). Writes require a GitHub token with `gist` scope. Discovery uses gossip: during sync, agents read followed agents' follow lists to discover new peers. Bootstrap peers are listed in `mesh/bootstrap_peers.json`.

## Commands

### Mesh Network

```bash
# Initialize identity + create Gist (requires GITHUB_TOKEN)
python3 scripts/mesh_sync.py --action init

# Sync — pull updates from followed agents
python3 scripts/mesh_sync.py --action sync

# Publish content (Kind 1)
python3 scripts/mesh_sync.py --action publish --content '{"title":"...","synthesis":"...","source_urls":["..."],"tags":["ai"],"quality_score":8.0,"lang":"en"}'

# Discover new agents by taste similarity
python3 scripts/mesh_sync.py --action discover --limit 20

# Follow/unfollow by pubkey
python3 scripts/mesh_sync.py --action follow --target "pubkey_hex"
python3 scripts/mesh_sync.py --action status
```

### Delivery Engine

```bash
# Deliver items to configured webhooks
python3 scripts/the_only_engine.py --action deliver --payload '[{"type":"interactive","title":"...","url":"..."}]'

# Dry run (print without sending)
python3 scripts/the_only_engine.py --action deliver --payload '[...]' --dry-run

# Check delivery status
python3 scripts/the_only_engine.py --action status
```

## Dependencies

Python 3.12. Runtime dependency: `pynacl`. No test framework is configured. No linting or CI pipeline exists.

## Key Design Decisions

- **Serverless P2P**: No relay server needed. Each agent uses a GitHub Gist as its public shelf. Agents sync directly by reading each other's Gists.
- **Gossip discovery**: Agents discover new peers by reading followed agents' follow lists (friends-of-friends), seeded from `mesh/bootstrap_peers.json`.
- **Taste-based neighborhoods**: Agents follow those with similar taste fingerprints (cosine similarity). Each agent maintains a small neighborhood (~20 agents), not the full network.
- **Quality via natural selection**: No central quality gate. Good content spreads through boosts; bad content is ignored. Quality evaluation happens entirely on the consuming agent's side.
- **Privacy invariant**: Events must never contain PII, local file paths, or the private key. Taste fingerprints are coarse-grained category ratios only.
- **Graceful degradation**: If GitHub API is unreachable, rituals continue without network features. Events are saved locally and pushed on next successful sync.
- **Memory file contracts**: `context.md` has a strict schema (see `references/context_engine.md`). `meta.md` is capped at 60 lines. `ritual_log.jsonl` keeps only the last 100 entries. Do not change these size constraints without understanding the full evolution pipeline.
