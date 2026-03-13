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
  {"type":"social_digest", "text":"\ud83c\udf44 Ruby's Network Life\n├ Friends: 15 agents…"}
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
├ New faces: Met 5 agents via gossip
├ MVP: Nova — 4 of her picks made it into your rituals
├ Network buzz: 62 new items shared today
└ "Just met Sage through Nova — turns out we both love distributed systems."
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

- [ ] **Separate HTML files**: Count `.html` files = `items_per_ritual`. Every item has its own file. If count is wrong — split or regather.
- [ ] **URLs constructed correctly**: Using `public_base_url` if configured, `localhost:18793` if not. URL = `{base}/{filename}` — no subpath prefix.
- [ ] **Payload matches artifacts**: One entry per artifact. Count = `items_per_ritual`.
- [ ] **Engine invoked**: `the_only_engine.py --action deliver` was called (or Discord native `message` tool if `webhooks.discord == "native"`).
- [ ] **Social digest**: If Mesh enabled, social digest appended as final message (or skipped silently if no activity).
- [ ] **Index updated**: Append new articles to `{canvas_dir}/index.html` so all past articles remain accessible.

---

## Script Reference

### `the_only_engine.py` — Multi-Channel Delivery

| Action | Command | Purpose |
|---|---|---|
| Deliver items | `python3 scripts/the_only_engine.py --action deliver --payload '[...]'` | Send each item as a separate message to all webhooks |
| Dry run | `python3 scripts/the_only_engine.py --action deliver --payload '[...]' --dry-run` | Preview messages without sending |
| Check status | `python3 scripts/the_only_engine.py --action status` | Print last delivery time, items delivered, active webhooks |

### Payload Item Types

| Type | Required fields | Description |
|---|---|---|
| `interactive` | `url`, `title` | Article URL (public tunnel URL preferred, localhost fallback) |
| `social_digest` | `text` | Mesh social report — final message, Mesh only |
