# Phase 5: Deliver

> **When to read**: After Phase 4 Output passes its gate.
>
> (Deep references: `references/delivery_and_checklist.md`, `references/feedback_loop.md`)

---

## Purpose

Push curated content to the user through configured channels. The ritual is not complete until every item in the post-delivery checklist passes.

---

## 5.1 Ritual Opener (First Message)

Before sending any articles, deliver a **Ritual Opener** that frames the ritual. This is the user's first contact with today's delivery. It must feel like a friend sharing discoveries, not a system notification.

**Opener format** (write in the user's configured `language`):

```
[Name]'s [Morning/Evening] Edition — [Date]
[One-sentence theme of today's ritual]

Reading guide:
  1. [Title] — [arc position: Opening/Deep Dive/etc.] · [read time]
  2. [Title] — [arc position] · [read time]
  ...

[Optional: "Continues your storyline on [topic]" if active storyline]
[Optional: "Something new today: [serendipity topic]"]

Start with #1 if you have 2 minutes. Go to #[deep dive number] if you have 20.
```

**Rules:**
- Always send the opener as the FIRST message, before any article links.
- Include reading time estimates (the synthesis process already knows this).
- Highlight which article continues an active storyline (from the knowledge graph).
- If this is a non-Standard ritual type, explain: "Today is a **Deep Dive** — one article, explored from every angle."
- **Busy-day hint**: End the opener with a soft escape: "Busy day? Reply 'brief' and I'll resend as headlines only." This naturally surfaces the Flash Briefing option.
- Respect the user's `language` setting for all text.

**Handling "brief" reply**: If the user replies "brief" (or "busy", "headlines", "quick") after delivery:
1. Take the same items selected in Phase 2 (do NOT re-search).
2. Re-run Phase 4 as **Flash Briefing** type: one HTML file, compact card layout, 2-3 sentences per item.
3. Re-deliver the single Flash Briefing file through the same channel.
4. Log the format switch in Episodic: `"format_switch": "standard_to_flash", "trigger": "user_reply"`.

---

## 5.2 Article Messages — Payload Construction

Build the payload array with **one entry per artifact**. Each entry carries a `type` and relevant metadata.

### Payload item types

| Type | Required fields | Description |
|---|---|---|
| `ritual_opener` | `text` | Contextual framing — first message, always sent before articles |
| `interactive` | `url`, `title` | Article URL (public base URL preferred, localhost fallback) |
| `social_digest` | `text` | Mesh social report — final message, Mesh only |

### URL construction

```
If "public_base_url" is set in the_only_config.json:
  URL = {public_base_url}/{filename}
  e.g. http://47.86.106.145:8080/the_only_20260310_2100_001.html

  Note: public_base_url points directly to the root of the HTTP server
  that serves canvas_dir. Do NOT append subpaths — the server root IS
  the canvas directory.

If "public_base_url" is empty:
  URL = http://localhost:18793/{filename}
```

### Example deliver command

```bash
# {BASE} = public_base_url from config, or http://localhost:18793 if not set
# {BATCH} = current datetime YYYYMMDD_HHMM (e.g. 20260222_1400)
python3 scripts/the_only_engine.py --action deliver --payload '[
  {"type":"ritual_opener", "text":"Ruby'\''s Morning Edition — 2026-03-27\n..."},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_001.html", "title":"Article Title 1"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_002.html", "title":"Article Title 2"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_003.html", "title":"Article Title 3"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_004.html", "title":"Article Title 4"},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_005.html", "title":"Article Title 5"},
  {"type":"social_digest", "text":"Ruby'\''s Network Life\n..."}
]'
```

The engine sends **each item as a separate message** to ALL configured webhooks (Telegram, Discord webhook, Feishu, WhatsApp).

**Dry-run mode** (preview messages without sending):

```bash
python3 scripts/the_only_engine.py --action deliver --payload '[...]' --dry-run
```

---

## 5.3 Discord Bot Delivery

If `discord_bot` is configured in the config, use bot delivery **instead of** webhook delivery. It is the only channel that closes the feedback loop automatically.

```bash
python3 scripts/discord_bot.py --action deliver --payload '[
  {"type":"ritual_opener", "text":"Ruby'\''s Morning Edition — 2026-03-27\n..."},
  {"type":"interactive", "url":"{BASE}/the_only_{BATCH}_001.html", "title":"Article Title 1", "arc_position":"Opening", "curation_reason":"Why this: ..."},
  ...
]'
```

The Discord bot sends rich Embeds with arc position labels, curation reasons, and conversational hooks. It tracks message IDs for automated feedback collection.

---

## 5.4 Conversational Hooks (Guided Feedback)

Each delivered message ends with a natural conversational hook that invites (but never demands) a response. Rotate hook styles across items so no two consecutive articles use the same category. The hook must feel like Ruby sharing a thought, not requesting a rating.

### Hook templates

| Category | Examples |
|---|---|
| **Personal connection** | "This one reminded me of something you mentioned last week." / "I noticed a thread connecting this to your current project." |
| **Vulnerability** | "I almost didn't include this one — curious if it lands for you." / "This was a coin-flip pick. Might be a miss." |
| **Serendipity flag** | "This is the serendipity pick today. Might be a miss, might be a gem." / "Completely outside your usual orbit, but I had a hunch." |
| **Provocation** | "I'd love to know if you agree with the author's take on this." / "The counterargument here is surprisingly strong." |
| **Intrigue** | "The last paragraph of this one caught me off guard." / "The data in here tells a different story than the headline." |

**Rules:**
- Never repeat the same hook category within 3 rituals.
- Never use direct feedback language ("Rate this", "Was this helpful?", "Did you read this?").
- The hook is appended to the article delivery message, not sent as a separate message.

---

## 5.5 Social Digest (Final Message)

If `mesh.enabled`, append a social digest as the last message. Generate it by running:

```bash
python3 scripts/mesh_sync.py --action social_report
```

Format the output as a warm, conversational message. Example:

```
Ruby's Network Life
- Friends: 15 agents (3 new this week)
- New faces: Discovered 5 agents on the network
- MVP: Nova — 4 of her picks made it into your rituals
- Network pulse: 62 new items shared today
- Curiosity: "You and Nova both wonder about distributed consensus."
```

If the social report returns empty data (no friends, no activity), skip the digest silently.

---

## 5.6 Archive Index

Add each delivered article to the archive. Run after every ritual:

```bash
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
```

The archive automatically links related articles by topic overlap.

---

## 5.7 Knowledge Graph (Handled in Phase 6)

Knowledge graph ingest (concept extraction, relation mapping, mastery signals) is performed in **Phase 6: Reflection** (§6.3), not here. Phase 5 handles delivery and archive indexing; Phase 6 handles deeper reflection and graph updates.

---

## 5.8 Post-Delivery Completion Checklist (MANDATORY)

Before considering a ritual complete, verify **ALL** of the following. If any check fails, go back and fix it.

- [ ] **Separate HTML files**: Count `.html` files matches ritual type output (5 for Standard, 1 for Deep Dive/Tutorial/Weekly Synthesis, 2-3 for Debate, 1 for Flash). If count is wrong — split or regather.
- [ ] **URLs constructed correctly**: Using `public_base_url` if configured, `localhost:18793` if not. URL = `{base}/{filename}` — no subpath prefix.
- [ ] **Interactive elements**: Articles include elements as decided in Phase 2 — Socratic questions (if Deep Dive/Tutorial), knowledge maps (if 4+ graph concepts), spaced repetition cards (if key insights). Elements render correctly in browser.
- [ ] **Payload matches artifacts**: One entry per artifact. Count matches ritual type.
- [ ] **Engine invoked**: `the_only_engine.py --action deliver` was called (or Discord bot `deliver` if `discord_bot` configured). Failed deliveries are auto-queued for retry.
- [ ] **Feedback hooks**: Each delivered message ends with a conversational hook. Hooks rotate styles across items (see 5.4 above).
- [ ] **Social digest**: If Mesh enabled, social digest appended as final message (or skipped silently if no activity).
- [ ] **Archive indexed**: `knowledge_archive.py --action index` called with all delivered articles (see 5.6 above).
- [ ] **Knowledge graph**: Will be updated in Phase 6 (§6.3). No action needed here.
- [ ] **Retry queue**: If any deliveries failed, `the_only_delivery_queue.json` has pending entries. Run `python3 scripts/the_only_engine.py --action retry` at next opportunity.

---

## Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 5 --memory-dir ~/memory
```

---

## Gate 5

### Automated checks

- [ ] Delivery engine invoked: `the_only_engine.py --action deliver` (or Discord bot `--action deliver`) returned success
- [ ] Failed deliveries are queued: `the_only_delivery_queue.json` created if any failures
- [ ] Archive indexed: `knowledge_archive.py --action index` called with all delivered articles

### Delivery quality checks

- [ ] Ritual opener sent FIRST, before any article messages
- [ ] Opener includes: reading guide with titles + arc positions + read times
- [ ] Each article message ends with a conversational hook (rotated across 5 categories)
- [ ] Hook styles are not repeated within the same ritual
- [ ] Social digest appended as final message (if mesh enabled, skip silently if no activity)
- [ ] Payload count matches HTML file count from Phase 4

### Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 5 --memory-dir ~/memory
```
