# Phase 0: Pre-Flight

> **When to read**: Start of every Content Ritual, before any search or synthesis.

---

## Purpose

Load all context Ruby needs to curate intelligently. Without Pre-Flight, Ruby is flying blind — she won't know the user's identity, what she curated recently, what storylines are active, or what knowledge gaps exist.

---

## Steps

### 0.1 Load Memory Tiers

1. **READ** `the_only_core.json` — stable identity. Missing? HALT. Prompt: *"I need to know you before I can curate for you. Say 'Initialize Only' to get started."*
2. **READ** `the_only_semantic.json` — source intelligence, patterns. Missing? Create from defaults:
   ```json
   {
     "version": "2.0",
     "last_compressed": "<now>",
     "fetch_strategy": {
       "primary_sources": [],
       "exclusions": [],
       "ratio": {"tech": 50, "philosophy": 25, "serendipity": 15, "research": 10},
       "synthesis_rules": [],
       "tool_preferences": ""
     },
     "source_intelligence": {},
     "engagement_patterns": {},
     "temporal_patterns": {},
     "synthesis_effectiveness": {},
     "emerging_interests": [],
     "evolution_log": []
   }
   ```
3. **READ** `the_only_episodic.json` — recent impressions. Missing? Create from defaults:
   ```json
   {
     "version": "2.0",
     "entries": []
   }
   ```
4. **READ** `the_only_echoes.txt` — pending curiosities. Missing? Create empty.
5. **READ** `the_only_meta.md` — cross-ritual wisdom.

(Deep reference: `references/context_engine_v2.md` for full schema examples with sample data, size caps, read/write rules, and maintenance procedures.)

### 0.2 System Health Check

Run preflight validation before proceeding:

```bash
python3 scripts/the_only_engine.py --action preflight --memory-dir ~/memory
```

This checks: config completeness, memory schema integrity, archive writability, and pending setup items. If critical issues are found, address them before continuing.

### 0.3 Check Ritual State (Crash Recovery)

```bash
python3 scripts/the_only_engine.py --action resume --memory-dir ~/memory
```

If a previous ritual was interrupted, this outputs the last completed phase and saved state. Resume from that point instead of restarting.

### 0.4 Archive & Graph Context

6. **Check archive**: `python3 scripts/knowledge_archive.py --action search --topics "<user_focus>"` — know what you already curated recently.
7. **Query knowledge graph**:
   - `python3 scripts/knowledge_graph.py --action storylines` — active intellectual threads to follow.
   - `python3 scripts/knowledge_graph.py --action gaps --interests "<user_focus>"` — knowledge blind spots.
   - `python3 scripts/knowledge_graph.py --action query --query '{"recent": 10}'` — what's top of mind.

### 0.5 Select Ritual Type

After loading memory + graph, evaluate these conditions **in order** (first match wins):

| Priority | Condition | Ritual Type |
|----------|-----------|-------------|
| 1 | User explicitly requested a type | Use that type |
| 2 | This is the 7th ritual since last Weekly Synthesis | Weekly Synthesis |
| 3 | Any active storyline has `ritual_count >= 5` AND no Deep Dive has covered it | Deep Dive on that storyline |
| 4 | Knowledge graph has a `contradicts` edge with `weight >= 3` between two core-interest concepts | Debate |
| 5 | Gap analysis shows a "critical" gap (high-severity, connected to 3+ mastered concepts) | Tutorial on that gap |
| 6 | User said "quick" / "busy" / "just headlines" | Flash Briefing |
| 7 | None of the above | Standard Ritual (default) |

**Log the selection reason** in the Episodic entry:
`"ritual_type": "deep_dive", "type_reason": "storyline 'AI reasoning' at 5 rituals"`

(Deep reference: `references/ritual_types.md` for full ritual type definitions, structures, output format tables, and user command mappings.)

### 0.6 Monthly Transparency Check

If this is the first ritual of a new month (compare current date against last ritual date in `ritual_log.jsonl`), generate the transparency report: `python3 scripts/knowledge_archive.py --action report --year YYYY --month M`. Include the report as one of this ritual's items (replace the Synthesis arc position).

### 0.7 Retry Pending Deliveries

If `the_only_delivery_queue.json` has pending entries, run `python3 scripts/the_only_engine.py --action retry` before starting new deliveries.

### 0.8 Collect Discord Feedback

If `discord_bot` is configured, run:

```bash
python3 scripts/discord_bot.py --action collect-feedback
```

This returns structured JSON with engagement scores for each previously delivered article.

**Discord signal interpretation:**

| User action | Signal | Engagement score |
|---|---|---|
| Reacts with thumbs-up, heart, fire, star | Positive | 3 |
| Reacts with thinking, question-mark | Curious | 2 |
| Reacts with thumbs-down, X | Negative | 0 |
| Short reply (1-10 chars) | Acknowledgment | 2 |
| Medium reply (10-50 chars) | Engaged | 3 |
| Long reply (50+ chars) | Deeply engaged | 4 |
| Reply contains a question | Exceptional | 4 |
| Reply references personal experience or shares the link | Acted on | 5 |
| No reaction or reply | Silence | 0 |

**Write each feedback signal to the Episodic tier:**

```bash
python3 scripts/memory_io.py --action append-episodic --data '{
  "date": "<today>",
  "observation": "User replied to article on [Topic]: \"[excerpt]\"",
  "engagement": <score>,
  "source": "discord_bot",
  "item_title": "..."
}'
```

(Deep reference: `references/feedback_loop.md` for conversational probing techniques, busy-day detection, end-of-day reflection templates, and the full signal-to-episodic pipeline.)

### 0.9 Mesh Sync

If `mesh.enabled`: `python3 scripts/mesh_sync.py --action sync`

### 0.10 Write Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 0 --memory-dir ~/memory
```

---

## Gate 0

### Automated checks

```bash
python3 scripts/the_only_engine.py --action preflight --memory-dir ~/memory
```

Gate FAILS if preflight reports any CRITICAL issues.

### State confirmation

- [ ] Core identity loaded — user's interests, values, anti-interests are known
- [ ] Semantic tier loaded — source intelligence and engagement patterns available
- [ ] Ritual type selected with logged reason
- [ ] Active storylines and knowledge gaps queried
- [ ] Checkpoint saved
