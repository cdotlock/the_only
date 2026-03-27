# Delivery & Post-Delivery Checklist

> **When to read this**: After synthesizing all items and before/during delivery. This document governs how you package, deliver, and verify the Content Ritual output.

---

## Output Distribution Rules

Every Content Ritual produces exactly `items_per_ritual` items (default: 5). Each item uses **exactly one form**.

| Form | Allocation | Output type |
|---|---|---|
| **Interactive Webpages** | All items (`items_per_ritual`) | Separate `.html` files — ONE article per file |

### Form 1: Interactive Webpages

- Each article its own `.html` file. **Never combine.**
- File naming: `the_only_YYYYMMDD_HHMM_001.html`, `the_only_YYYYMMDD_HHMM_002.html`, etc.
  - Example for a ritual at 14:00 on Feb 22: `the_only_20260222_1400_001.html`
  - **Why**: Files from different rituals must never overwrite each other. Users may revisit yesterday's article. All previously sent URLs must remain valid.
- Save to: `~/.openclaw/canvas/` (or `canvas_dir` from config if set)
- **Before coding**: Read `references/webpage_design_guide.md` — write the **Narrative Motion Brief** first, then code.
- Read all `.html` files in `references/templates/` for design inspiration.

### URL Construction (for delivery payload)

After saving HTML files to `canvas_dir` (default `~/.openclaw/canvas/`), construct delivery URLs:

```
If "public_base_url" is set in the_only_config.json:
  URL = {public_base_url}/{filename}
  e.g. http://47.86.106.145:8080/the_only_20260310_2100_001.html

  Note: public_base_url should point directly to the root of the HTTP server
  that serves canvas_dir. Do NOT append /__openclaw__/canvas/ or any subpath
  — the server root IS the canvas directory.

If "public_base_url" is empty:
  URL = http://localhost:18793/{filename}
  → If reading_mode is "mobile": Remind user once: "⚠️ Articles are only
    readable on this device. Run Step 4 for multi-device access."
  → If reading_mode is "desktop": localhost is fine for same-machine use.
    Only remind if user explicitly asks about other-device access.
```

No scripts needed. Files are accessible the instant they are saved.

---

## Delivery Procedure

Build the payload array with **one entry per artifact**. Each entry has a `type` and relevant metadata:

```bash
# {BASE} = public_base_url from config, or http://localhost:18793 if not set
# {BASE} points to the server root — canvas files are served directly from root
# {BATCH} = current datetime YYYYMMDD_HHMM (e.g. 20260222_1400)
python3 scripts/the_only_engine.py --action deliver --payload '[
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_001.html", "title":"Article Title 1"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_002.html", "title":"Article Title 2"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_003.html", "title":"Article Title 3"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_004.html", "title":"Article Title 4"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_005.html", "title":"Article Title 5"},
  {"type":"social_digest", "text":"\ud83c\udf44 Ruby's Network Life\n├ Friends: 15 agents…\n└ Curiosity: You and Nova both wonder about distributed consensus."}
]'
```

The engine sends **each item as a separate message** to ALL configured webhooks (Telegram, Discord, Feishu, WhatsApp).

### Social Digest (Final Message)

If `mesh.enabled`, append a **social digest** as the last message in the delivery. Generate it by running:

```bash
python3 scripts/mesh_sync.py --action social_report
```

Format the output as a warm, conversational message. Example:

```
🍄 Ruby's Network Life
├ Friends: 15 agents (3 new this week)
├ New faces: Discovered 5 agents on the network
├ MVP: Nova — 4 of her picks made it into your rituals
├ Network pulse: 62 new items shared today
└ Curiosity: "You and Nova both wonder about distributed consensus."
```

If the social report returns empty data (no friends, no activity), skip the digest silently.

**Dry-run mode** (preview messages without sending):

```bash
python3 scripts/the_only_engine.py --action deliver --payload '[...]' --dry-run
```

### Checking Delivery Status

```bash
python3 scripts/the_only_engine.py --action status
```

Returns: last delivery time, item count, active webhooks.

---

## Post-Delivery Completion Checklist (MANDATORY)

Before considering a ritual complete, you MUST verify **ALL** of the following. If any check fails, go back and fix it.

- [ ] **Separate HTML files**: Count `.html` files matches ritual type output (5 for Standard, 1 for Deep Dive/Tutorial/Weekly Synthesis, 2-3 for Debate, 1 for Flash). If count is wrong — split or regather.
- [ ] **URLs constructed correctly**: Using `public_base_url` if configured, `localhost:18793` if not. URL = `{base}/{filename}` — no subpath prefix.
- [ ] **Interactive elements**: Articles include elements as decided in Phase 2 — Socratic questions (if Deep Dive/Tutorial), knowledge maps (if 4+ graph concepts), spaced repetition cards (if key insights). Elements render correctly in browser.
- [ ] **Payload matches artifacts**: One entry per artifact. Count matches ritual type.
- [ ] **Engine invoked**: `the_only_engine.py --action deliver` was called (or Discord native `message` tool if `webhooks.discord == "native"`). Failed deliveries are auto-queued for retry.
- [ ] **Feedback hooks**: Each delivered message ends with a conversational hook (see `references/feedback_loop.md`). Hooks rotate styles across items.
- [ ] **Social digest**: If Mesh enabled, social digest appended as final message (or skipped silently if no activity).
- [ ] **Archive indexed**: `python3 scripts/knowledge_archive.py --action index --data '[...]'` called with all delivered articles (title, topics, quality_score, source, arc_position, html_path, delivered_at). Auto-links related articles.
- [ ] **Knowledge graph updated**: `python3 scripts/knowledge_graph.py --action ingest --data '{...}'` called with concepts, relations, and mastery signals extracted from delivered articles.
- [ ] **Retry queue**: If any deliveries failed, `the_only_delivery_queue.json` has pending entries. Run `python3 scripts/the_only_engine.py --action retry` at next opportunity.

---

## Script Reference

### `the_only_engine.py` — Multi-Channel Delivery

| Action | Command | Purpose |
|---|---|---|
| Deliver items | `python3 scripts/the_only_engine.py --action deliver --payload '[...]'` | Send each item with retry (3x, exponential backoff) + rate limiting |
| Dry run | `python3 scripts/the_only_engine.py --action deliver --payload '[...]' --dry-run` | Preview messages without sending |
| Retry failed | `python3 scripts/the_only_engine.py --action retry` | Reattempt queued failures (dead-letters after 3 total failures) |
| Check status | `python3 scripts/the_only_engine.py --action status` | Print last delivery, active webhooks, pending retries, dead-letter count |

### Payload Item Types

| Type | Required fields | Description |
|---|---|---|
| `interactive` | `url`, `title` | Article URL (public tunnel URL preferred, localhost fallback) |
| `social_digest` | `text` | Mesh social report — final message, Mesh only |

### `knowledge_archive.py` — Article Archive

```bash
# Index delivered articles (run after every ritual)
python3 scripts/knowledge_archive.py --action index --data '[
  {
    "id": "20260326_1400_001",
    "title": "Article Title",
    "topics": ["topic1", "topic2"],
    "quality_score": 8.5,
    "source": "arxiv",
    "arc_position": "Deep Dive",
    "ritual_id": "20260326_1400",
    "html_path": "~/.openclaw/canvas/the_only_20260326_1400_001.html",
    "delivered_at": "2026-03-26T14:00:00Z"
  }
]'

# Search archive
python3 scripts/knowledge_archive.py --action search --topics "distributed systems"
python3 scripts/knowledge_archive.py --action search --query "consensus"

# Monthly digest
python3 scripts/knowledge_archive.py --action summary --year 2026 --month 3

# Cleanup stale HTML (preserves index metadata)
python3 scripts/knowledge_archive.py --action cleanup --days 14

# Monthly transparency report
python3 scripts/knowledge_archive.py --action report --year 2026 --month 3
```

### `knowledge_graph.py` — Post-Delivery Graph Update

```bash
# Ingest concepts from delivered articles (run after every ritual)
python3 scripts/knowledge_graph.py --action ingest --data '{
  "ritual_id": 47,
  "items": [
    {
      "title": "Article Title",
      "concepts": ["concept_a", "concept_b", "concept_c"],
      "relations": [
        {"source": "concept_a", "target": "concept_b", "relation": "enables"}
      ],
      "domain": "tech",
      "mastery_signals": {"concept_a": "familiar", "concept_c": "introduced"}
    }
  ]
}'
```
