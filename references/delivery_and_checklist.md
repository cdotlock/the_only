# Delivery & Post-Delivery Checklist

> **When to read this**: After synthesizing all items and before/during delivery. This document governs how you package, deliver, and verify the Content Ritual output.

---

## Output Distribution Rules

Every Content Ritual produces exactly `items_per_ritual` items (default: 5). Each item uses **exactly one form**.

| Form | Allocation | Output type |
|---|---|---|
| **Interactive Webpages** | Majority (e.g., 4 of 5) | Separate `.html` files — ONE article per file |
| **NanoBanana Infographic** | At least 1 per ritual | Direct `nano-banana-pro` skill call — no HTML |

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

### Form 2: NanoBanana Pro Infographic (MANDATORY)

- **THIS IS NOT OPTIONAL.** Every ritual MUST include at least one NanoBanana infographic.
- Choose the most **data-dense or logically complex** topic for the infographic.
- Call the `nano-banana-pro` skill directly. Do NOT wrap the result in HTML. Let the skill produce its own visual output.
- **Prompt quality**: Follow the **NanoBanana Prompt Construction Procedure** below. Never write a prompt without completing all 4 steps.

### NanoBanana Prompt Construction Procedure (MANDATORY)

> **The #1 problem**: Without explicit guidance, AI image generators default to cold, mechanical, tech-poster aesthetics — glowing circuits, dark sci-fi backdrops, rigid geometric grids. The result looks like a stock LinkedIn infographic. **This is the opposite of what we want.**

**Goal**: Every NanoBanana infographic should feel like it was **hand-illustrated by a talented editorial artist** — the kind of visual you'd find in The New York Times Sunday Edition, Monocle magazine, or a beautifully typeset textbook from the 1960s. Think: warmth, craftsmanship, personality.

#### Step 1: Identify the Core Visual Metaphor

Before writing any prompt, ask yourself: **"What does this topic look like as a physical object or natural phenomenon?"**

| Topic domain | Natural visual metaphor | NOT this |
|---|---|---|
| Networks, connections | Root systems, river deltas, mycelium | Circuit boards, node graphs |
| Growth, progress | Trees, seedlings, geological strata | Bar charts, upward arrows |
| Complexity, systems | Cross-section illustrations, cutaway diagrams | Flowcharts, block diagrams |
| Data, statistics | Botanical illustration with data labels, annotated maps | Dashboard screenshots |
| Comparison | Side-by-side specimen illustrations | Versus screens, split panels |
| Process, flow | Watercolor wash flowing between stations | Pipeline arrows, conveyor belts |
| History, time | Aged paper, journal entries, timeline as landscape | Digital timelines, neon dates |

#### Step 2: Choose a Visual Archetype

Select ONE archetype that matches the metaphor. Each has a distinct visual language:

| Archetype | When to use | Key style words |
|---|---|---|
| **Botanical Illustration** | Biology, ecology, growth, networks | "Detailed botanical illustration, fine ink linework, watercolor washes, specimen labels, aged parchment" |
| **Cartographic** | Geography, systems, journeys, exploration | "Hand-drawn map, topographic contours, compass rose, warm sepia ink, cartouche labels" |
| **Cross-Section / Cutaway** | Technology, engineering, 'how it works' | "Cross-section cutaway illustration, technical pen, labeled parts, Da Vinci notebook style" |
| **Journal / Field Notes** | Research findings, observations, discoveries | "Field journal page, handwritten annotations, pressed specimens, coffee-stained paper, sketches in margins" |
| **Culinary / Recipe** | Processes, recipes, step-by-step | "Illustrated recipe card, ingredient sketches, hand-lettered steps, warm kitchen palette" |
| **Astronomical Chart** | Space, scale, cosmic topics, big-picture thinking | "Vintage star chart, celestial illustration, gold leaf accents, deep navy background, observatory line art" |
| **Architectural Blueprint** | Design, planning, structure, frameworks | "Blueprint sketch, architect's hand-drawn elevation, trace paper texture, blue-white palette" |
| **Naturalist's Notebook** | Classification, comparison, taxonomy | "Naturalist field guide plate, species comparison, fine crosshatching, muted earth tones, Latin labels" |

#### Step 3: Construct the Prompt

Every NanoBanana prompt MUST include these 5 components:

```
1. SUBJECT:  "Create a visual knowledge map about '[Topic Title]'."
2. ARCHETYPE: "Style: [chosen archetype] with [2-3 specific style details]."
3. PALETTE:  "Color palette: [3-4 specific colors, warm/organic]."
4. NODES:   "Key concepts: 1) [Node] 2) [Node] 3) [Node] 4) [Node] 5) [Node]."
5. FLOW:    "Visual flow: [how concepts connect — use organic metaphors, not arrows]."
```

**Mandatory style suffix** — always append ONE of these to the end of the prompt:

- "Hand-drawn quality with visible pen strokes and slight imperfections that feel human."
- "Textured paper background with subtle grain, as if drawn in a premium sketchbook."
- "Editorial illustration quality — the kind of visual that belongs in a beautifully printed magazine."

#### Step 4: Anti-Pattern Check

Before sending the prompt, verify it does NOT contain any of these words or concepts:

**BLACKLISTED — these trigger mechanical/AI aesthetics:**

| Category | Banned words |
|---|---|
| Sci-fi | futuristic, cyber, neon, holographic, sci-fi, matrix, laser, digital rain |
| Tech | circuit board, motherboard, code overlay, data stream, binary, pixel, wireframe, dashboard |
| Corporate | PowerPoint, infographic template, corporate, professional, modern minimalist, flat design |
| Dark/Glow | glowing, luminous, dark mode, black background, LED, backlit |
| Generic AI | abstract, conceptual art, 3D render, photorealistic, CGI, artificial |

If any blacklisted word appears in your prompt, replace it with an organic alternative from the archetype vocabulary.

### Calibration Examples

**Topic: How Trees Communicate Underground**
> "Create a visual knowledge map about 'How Trees Communicate Underground'. Style: botanical illustration with fine ink linework, watercolor washes in forest greens and amber, on aged cream parchment. Color palette: forest green, warm amber, sepia, cream. Key concepts: 1) Mycorrhizal networks 2) Chemical signaling 3) Resource sharing 4) Mother trees 5) Forest resilience. Visual flow: root-like tendrils drawn in sepia ink connect each concept node, spreading outward from a central mother tree illustration, with each node rendered as a naturalist's specimen label. Hand-drawn quality with visible pen strokes and slight imperfections that feel human."

**Topic: The Economics of Attention**
> "Create a visual knowledge map about 'The Economics of Attention'. Style: field journal page with handwritten annotations, small margin sketches, and coffee-stained paper texture. Color palette: warm sepia, dusty rose, faded teal, cream. Key concepts: 1) Attention as currency 2) The scarcity paradox 3) Notification fatigue 4) Deep work economics 5) The attention dividend. Visual flow: concepts arranged as entries in a researcher's notebook, connected by hand-drawn bracket annotations and small illustrative doodles — an hourglass for scarcity, a bell for notifications, a candle for deep work. Textured paper background with subtle grain, as if drawn in a premium sketchbook."

**Topic: How Transformers Process Language**
> "Create a visual knowledge map about 'How Transformers Process Language'. Style: cross-section cutaway illustration, technical pen on trace paper, Da Vinci notebook aesthetic with labeled parts and dimensional arrows. Color palette: warm ivory, burnt sienna, charcoal grey, touches of copper. Key concepts: 1) Tokenization 2) Embedding space 3) Attention mechanism 4) Layer stacking 5) Output prediction. Visual flow: rendered as a cross-section of an imaginary machine — like a vintage scientific instrument cutaway — where each concept is a visible internal component with hand-lettered labels and annotation lines. Editorial illustration quality — the kind of visual that belongs in a beautifully printed magazine."

> If `nano-banana-pro` is not available: Inform the user: "NanoBanana Pro skill not found. Please install it for infographic generation." Convert this item to a webpage instead, but log the missing skill to the Ledger.

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
  {"type":"nanobanana", "title":"Infographic Title", "prompt":"…"},
  {"type":"social_digest", "text":"🍄 Ruby's Network Life\n├ Friends: 15 agents…"}
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

- [ ] **Separate HTML files**: Count `.html` files = number of webpage items. If count is 1 but articles > 1 — split them.
- [ ] **URLs constructed correctly**: Using `public_base_url` if configured, `localhost:18793` if not. URL = `{base}/{filename}` — no subpath prefix.
- [ ] **NanoBanana called**: Invoked `nano-banana-pro` with a hand-drawn style directive. If not — do it now.
- [ ] **Each item uses one form**: No item as both webpage and infographic.
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
| `nanobanana` | `title`, `prompt` | NanoBanana infographic metadata |
| `social_digest` | `text` | Mesh social report — final message, Mesh only |
