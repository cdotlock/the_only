# Phase 4: Output — HTML Generation

> **When to read**: After Phase 3 Narrative Arc passes its gate.
>
> (Design inspiration: `references/templates/` contains reference HTML files.)

---

## Purpose

Generate beautiful, interactive HTML articles. This phase covers the design system, file rules, narrative motion brief, output format per ritual type, validation, and delivery file construction. Everything needed to go from Phase 3's narrative arc to finished, deliverable HTML is here.

---

## The Absolute Rule: ONE Article Per File

> **You must NEVER put more than one article into a single HTML file.**

- If you have 3 articles, you produce 3 separate `.html` files.
- Combining articles into one file — even as "sections", "cards", or a "scrolling magazine" — is a **VIOLATION**.
- One article = one file. One headline = one file. Period.
- **Exception**: Flash Briefing puts all items in a single HTML file (the only permitted exception).

**Self-check**: After coding, count your HTML files. The count MUST equal the number of items for the ritual type. If count is 1 but items > 1, you have failed — go back and split them.

---

## File Naming Convention

```
the_only_YYYYMMDD_HHMM_NNN.html
```

- `YYYYMMDD_HHMM` = ritual timestamp (e.g. `20260222_1400`)
- `NNN` = zero-padded sequence number (`001`, `002`, ..., matching the article's arc position)
- Example for a 5-item ritual at 14:00 on Feb 22:
  - `the_only_20260222_1400_001.html`
  - `the_only_20260222_1400_002.html`
  - `the_only_20260222_1400_003.html`
  - `the_only_20260222_1400_004.html`
  - `the_only_20260222_1400_005.html`

**Why timestamped**: Files from different rituals must never overwrite each other. Users may revisit yesterday's article. All previously sent URLs must remain valid.

**Save to**: `~/.openclaw/canvas/` (or `canvas_dir` from config if set).

---

## URL Construction (for delivery payload)

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
  - If reading_mode is "mobile": Remind user once: "Articles are only
    readable on this device. Run Step 4 for multi-device access."
  - If reading_mode is "desktop": localhost is fine for same-machine use.
    Only remind if user explicitly asks about other-device access.
```

No scripts needed. Files are accessible the instant they are saved.

---

## Narrative Motion Brief (MANDATORY — write before coding each article)

> **This is the most important step.** Before writing any HTML or CSS, think about the article as a *reading experience* — not a document. The animations should be a natural extension of the content's meaning, not a generic template applied on top.

For each article, produce this brief in your working thoughts:

```
Article: [Title]
Dominant metaphor: [One word/phrase that captures the essence — e.g. "orbital gravity",
  "fungal network", "memory fade", "tectonic shift"]

Scroll Journey:
  Act 1 — Opening (0-25% scroll): [The ambient state before content. What does the page
    feel like at rest? e.g. "Deep void, faint starfield at 5% opacity, absolute stillness"]
  Act 2 — Immersion (25-70% scroll): [Content reveals. What builds, emerges, or
    intensifies? e.g. "Moon crests the horizon, light spills across the text, shadows recede"]
  Act 3 — Resolution (70-100% scroll): [The emotional peak and release. e.g. "Full lunar
    light, the takeaway card glows warmly, the moon pulses once as a period at the end"]

Color journey: [How the palette shifts across the page — e.g. "#050510 -> #0d1a3a -> #1a2a5e,
  accented with soft silver-white"]

Signature moment: [The ONE scene that will surprise the reader. The unexpected delight.
  e.g. "As the reader reaches the pull quote, a crescent SVG slowly rotates into full circle"]

Animation restraint level: [1=subtle/minimal, 2=moderate, 3=theatrical]
  Default to 2. Only use 3 for truly cosmic/dramatic topics.
```

**Only after completing the brief should you start coding.** The brief is the design. The code is the render.

(Design inspiration: `references/templates/` contains 3 reference HTML files — cosmic, data, and organic themes. Read them when you want to study visual quality benchmarks or need CSS/animation patterns. Not required for execution — the design system below provides all structural rules.)

---

## Design System

### Color Palette

Use a **dark, sophisticated palette**. Never use raw CSS color names (no `red`, `blue`, `green`). Use HSL or curated hex values:

```css
:root {
  /* Background layers */
  --bg-primary: #0a0a0f;        /* Deep dark base */
  --bg-secondary: #12121a;      /* Slightly lighter for cards */
  --bg-tertiary: #1a1a2e;       /* Elevated surfaces */

  /* Accent colors — pick ONE warm accent per article */
  --accent-ruby: #e74c6f;       /* Signature Ruby red-pink */
  --accent-amber: #f0a500;      /* Warm gold */
  --accent-cyan: #00d4aa;       /* Cool teal */
  --accent-violet: #8b5cf6;     /* Deep purple */

  /* Text hierarchy */
  --text-primary: #f0f0f5;      /* Headlines, key text */
  --text-secondary: #a0a0b8;    /* Body text */
  --text-tertiary: #606078;     /* Captions, metadata */

  /* Functional */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --glow-accent: rgba(231, 76, 111, 0.15);  /* For Echo items */
}
```

**Vary the accent color** between articles to give each its own identity. Article 001 might use `--accent-ruby`, Article 002 uses `--accent-cyan`, etc.

### Typography

**Load Google Fonts via CDN with system font fallbacks.** If the CDN is unreachable, articles gracefully degrade to high-quality system fonts with no functional loss.

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

```css
:root {
  --font-serif: 'Playfair Display', 'Noto Serif SC', 'Source Han Serif', Georgia, 'Times New Roman', serif;
  --font-sans: 'Inter', 'Noto Sans SC', 'Source Han Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
}
```

Always use `var(--font-serif)`, `var(--font-sans)`, `var(--font-mono)` — never font family names directly. This ensures CJK text renders properly even without Google Fonts.

| Element | Font | Weight | Size | Notes |
|---|---|---|---|---|
| Headline | Playfair Display | 700-800 | 2.5-3.5rem | Dramatic, serif. Must feel premium. |
| Subheadline | Inter | 300 | 1.2-1.4rem | Clean contrast with headline. |
| Body text | Inter | 400 | 1.05-1.1rem | Line-height: **1.75**. Letter-spacing: 0.01em. |
| Code / data | JetBrains Mono | 400 | 0.9rem | For inline code, data callouts. |
| Metadata | Inter | 500 | 0.75rem | Uppercase, letter-spacing: 0.15em. Category labels, dates. |

### Key Spacing & Layout Rules

- Body content max-width: **680px centered** (desktop), full-width with 1rem padding (mobile).
- Use generous, intentional spacing: `2rem+` between sections. No `margin: 10px`.
- **No sidebar, no navigation bar, no footer links.** This is a reading experience, not a website.
- Default to desktop layout if `reading_mode` is not set.
- Headlines must be **large and dramatic** — never smaller than 2.5rem (desktop) or 1.8rem (mobile).
- Body line-height must be **1.75** (desktop) or 1.7 (mobile).
- Mobile: all interactive elements >= 48px touch targets. Minimal animations (fade-in only, conserve battery). Progress bar at bottom (thumb-reachable).
- Desktop: full entrance animations + signature moment. Progress bar at top.

### Scroll Reveal Pattern (MANDATORY)

Use the `.reveal` class on individual elements for scroll-triggered animations. **Never** put `opacity: 0` on large container divs.

**Required implementation:**

1. Add `.reveal` to every paragraph, blockquote, card, and interactive element that should animate in.
2. CSS:
   ```css
   .reveal { opacity: 0; transform: translateY(24px); transition: opacity 0.7s cubic-bezier(0.16,1,0.3,1), transform 0.7s cubic-bezier(0.16,1,0.3,1); }
   .reveal.visible { opacity: 1; transform: translateY(0); }
   ```
3. JS IntersectionObserver:
   ```javascript
   const observer = new IntersectionObserver((entries) => {
     entries.forEach(entry => {
       if (entry.isIntersecting) {
         entry.target.classList.add('visible');
         observer.unobserve(entry.target); // prevent re-trigger, free memory
       }
     });
   }, { threshold: 0.15, rootMargin: '0px 0px -10% 0px' });
   document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
   ```
4. Fallback for no-JS: `<noscript><style>.reveal { opacity: 1; transform: none; }</style></noscript>`

**Anti-pattern:** Never observe large wrapper divs (`.body-section`, `.article-container`). If a container is taller than the viewport, threshold 0.15 may never trigger — the content stays invisible. Always observe individual elements (paragraphs, quotes, cards).

### Article-Specific Animation Signatures

Each arc position has a distinct visual personality. **Do not use identical animations across all articles** — the visual rhythm should mirror the narrative rhythm.

| Arc Position | Accent Color | Animation Signature | Design Emotion |
|---|---|---|---|
| **Opening** | `#3498db` (blue) | Minimalist: pure `.reveal` fade-in + progress bar. No extra effects. Clean like turning the first page of a book. | Calm curiosity |
| **Deep Dive** | `#8b5cf6` (violet) | Richest: scroll-driven `--scroll-pct` CSS variable for background gradient shift. Pull quotes animate border-left on scroll. Section dividers fade in. Code blocks highlight on enter. Mermaid diagram fades in with delay. | Immersion, depth |
| **Surprise** | `#f0a500` (amber) | Unexpected: key paragraphs slide from the side (`translateX(-40px)` instead of `translateY`). Or parallax differential scrolling on pull quote. The reader should feel a subtle "wait, what?" | Delightful disruption |
| **Contrarian** | `#e74c3c` (red) | Tension: warmer/darker palette shift. Grid background with subtle `skewY` distortion on scroll. Pull quotes use inverted colors (light text on accent-tinted background). | Challenge, discomfort |
| **Synthesis** | `#2ecc71` (green) | Connection: `.synthesis-bridge` section with color-coded dots referencing each prior article's accent. Thread lines or animated connections between referenced concepts. | Resolution, coherence |

**Deep Dive implementation reference** (scroll-driven effects):
```javascript
window.addEventListener('scroll', () => {
  const pct = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight);
  document.documentElement.style.setProperty('--scroll-pct', pct);
});
```
```css
body { background: color-mix(in srgb, var(--bg-primary) calc((1 - var(--scroll-pct, 0)) * 100%), var(--bg-tertiary)); }
```

**Surprise implementation reference** (side-slide):
```css
.reveal-side { opacity: 0; transform: translateX(-40px); transition: opacity 0.7s cubic-bezier(0.16,1,0.3,1), transform 0.7s cubic-bezier(0.16,1,0.3,1); }
.reveal-side.visible { opacity: 1; transform: translateX(0); }
```

**Principle**: The animation signature expresses the narrative emotion, not decoration. Opening's restraint and Deep Dive's richness form a contrast — that contrast itself is the design.

### Deep Dive Mandatory Requirements

When generating the **Deep Dive** article (whether in Standard ritual or standalone):

1. **Length**: 8-12 minutes reading time (Chinese ≥ 2,400 characters / English ≥ 1,600 words). This is the intellectual core of the ritual — do not truncate.
2. **Mermaid knowledge map**: MUST include at least one `<pre class="mermaid">` diagram showing how the article's concepts connect to the knowledge graph. Generate via `python3 scripts/knowledge_graph.py --action visualize`.
3. **Table of Contents**: Include a clickable TOC with section navigation at the top (after the hook, before the first body section).
4. **Section structure**: 4-6 clearly delineated sections with `<h2>` subheadings, each building on the previous.
5. **Pull quotes**: At least 2 pull quotes highlighting key insights.
6. **Code/data**: If the topic is technical, include at least 1 code block or data visualization.

---

## Output Format Per Ritual Type

### Standard Ritual — 5 HTML files, 1-2 min each

- Each article is its own `.html` file.
- Include a "Previously on..." section if the knowledge graph shows related concepts from past rituals. Use `python3 scripts/knowledge_graph.py --action query --query '{"cluster": "<main_concept>"}'` to find connections.
- Narrative arc position indicator: a subtle label showing this item's role ("Opening / Deep Dive / Surprise / Contrarian / Synthesis").
- Interactive elements as decided in Phase 2: Socratic questions (0-1 per article), thought experiments, knowledge maps (when 4+ graph concepts connect), spaced repetition cards (1-2 per article).
- Knowledge map (Mermaid diagram) generated via `python3 scripts/knowledge_graph.py --action visualize --query '{"center": "<concept>", "hops": 2}'`.
- Special elements: narrative arc labels, "Previously on..."

### Deep Dive — 1 HTML file, 8-12 min

- Table of contents with section navigation.
- Full knowledge map showing the topic's graph neighborhood.
- 2-3 Socratic questions at natural pause points.
- Comprehensive "Previously on..." connecting to past rituals on this topic.
- Spaced repetition cards for key insights (1-2).
- Internal structure:
  1. **Context** — Why this matters now. Connect to what the user already knows.
  2. **Mechanism** — How it works, explained progressively. First principles up.
  3. **Evidence** — Primary sources, data, expert positions. Evaluate conflicting claims.
  4. **Debate** — Steel-man the opposing view. What could go wrong? Who disagrees and why?
  5. **Implications** — What changes if this is true? What should the user do differently?
  6. **Connections** — How this connects to other concepts in the knowledge graph. Include a Mermaid diagram.
  7. **Open Questions** — What we still don't know. Seed for future rituals.
- Special elements: table of contents, knowledge map, section navigation.

### Debate — 2-3 HTML files, 3-5 min each

- Each position gets its own article with equal visual treatment (equal word count and argument quality).
- Include a "What would change your mind?" section in each.
- Final synthesis article includes a decision matrix or comparison table.
- The synthesis does not "pick a winner" — it maps the decision space.
- If Ruby has a position, she states it transparently as her own.
- Special elements: side-by-side comparison, "What would change your mind?"

### Tutorial — 1 HTML file, 5-8 min

- Progressive disclosure layout: each section builds on the previous.
- Practice questions with reveal-to-check answers.
- Knowledge map showing where this concept sits relative to what the user already knows.
- Spaced repetition cards for each key definition/insight.
- Internal structure:
  1. **The Hook** — Why you should care (connect to something they already know).
  2. **Intuition** — Explain it like you're at a whiteboard with a friend. Analogy first.
  3. **Formal Definition** — Precise version. Jargon allowed because intuition is established.
  4. **Worked Example** — Walk through a concrete case step by step.
  5. **Edge Cases** — Where the intuition breaks down. What's surprising?
  6. **Practice Questions** — 2-3 Socratic questions that test understanding.
  7. **Knowledge Map** — Mermaid diagram showing where this concept sits in the graph.
- Special elements: progressive disclosure, practice questions, knowledge map.

### Weekly Synthesis — 1 HTML file, 5-8 min

- Storyline timeline visualization.
- This week's knowledge graph growth (Mermaid diagram).
- Connections across the week's rituals.
- Questions seeded for next week.
- Internal structure:
  1. **This Week's Thread** — What was the implicit theme across this week's rituals?
  2. **Connections You Might Have Missed** — Cross-item links not obvious in individual rituals.
  3. **Storyline Updates** — How each active storyline progressed.
  4. **Knowledge Growth** — What concepts moved up in mastery? What's new?
  5. **Visual Map** — Mermaid diagram of this week's concept cluster.
  6. **Questions for Next Week** — What Ruby is curious about for upcoming rituals.
- Special elements: storyline timeline, weekly knowledge graph.

### Flash Briefing — 1 HTML file (all items), 3-5 min total

- **Exception to one-article-per-file rule**: all items in a single HTML file.
- Compact card layout. **No interactive elements. No animations.**
- Mobile-optimized. Maximum information density.
- Each item: 2-3 sentences max. One core insight. One "so what."
- No narrative frills, no analogies, no cross-references.
- Uses a simplified mobile-first layout, not the full design system.

### Summary Table

| Type | Files | Approx Length | Special Elements |
|------|-------|---------------|-----------------|
| Standard | 5 HTML files | 1-2 min each | Narrative arc labels, "Previously on..." |
| Deep Dive | 1 HTML file | 8-12 min | Table of contents, knowledge map, section navigation |
| Debate | 2-3 HTML files | 3-5 min each | Side-by-side comparison, "What would change your mind?" |
| Tutorial | 1 HTML file | 5-8 min | Progressive disclosure, practice questions, knowledge map |
| Weekly Synthesis | 1 HTML file | 5-8 min | Storyline timeline, weekly knowledge graph |
| Flash Briefing | 1 HTML file | 3-5 min total | Compact cards, no animations |

All types except Flash Briefing follow the design system above. Flash Briefing uses a simplified mobile-first layout.

---

## Anti-Patterns (What NOT to Do)

| Don't | Do instead |
|---|---|
| Put multiple articles in one file | ONE article per file (Flash Briefing excepted) |
| Use plain white background | Use dark theme with `--bg-primary` |
| Use system fonts only | Load Google Fonts (Inter, Playfair Display, JetBrains Mono) |
| Use raw colors (`red`, `blue`) | Use curated palette from `:root` variables |
| Skip animations entirely | Include progress bar + fade-in at minimum |
| Use card grids for single article | Use full-page, single-column reading layout |
| Add navigation bars, sidebars | Keep it minimal — reading experience only |
| Use `<h1>` smaller than 2.5rem | Headlines must be dramatic and large |
| Set line-height below 1.6 | Body line-height must be 1.75 |
| Add placeholder images | Only include images if you have real content |
| Use generic CSS (`margin: 10px`) | Use generous, intentional spacing (`2rem+`) |
| Skip the Narrative Motion Brief | Write the brief first, then code |
| Observe `.body-section` with IntersectionObserver | Observe individual `.reveal` elements (see Scroll Reveal Pattern) |
| Show quality scores in HTML (e.g., "Score 8.05") | Scores are internal data — never expose to reader |

### Data Visibility Boundary

**User-visible metadata** (show in HTML):
- Source attribution
- Publication date
- Reading time estimate
- Arc position label (Opening / Deep Dive / Surprise / Contrarian / Synthesis)
- "Why This" curation reason

**Internal data** (NEVER show in HTML):
- Quality scores, composite scores, or any numeric rating (e.g., "Score 8.05")
- Engagement metrics (0-5 scale)
- Graph-level modifiers (tension, cross-domain bonus, redundancy penalty)
- Source intelligence scores (reliability, quality_avg)
- Mastery levels (introduced/familiar/understood/mastered) — used to calibrate tone, never to display
- Any `_internal`, `_debug`, or `_score` field

The user should feel curated insight, not algorithmic output. Scores belong in the archive index and episodic memory, not in the reading experience.

---

## Quality Benchmark

Before finalizing each HTML file, self-check:

1. Does this look like it was designed by a professional editorial team? If not, iterate.
2. Is the headline impactful at first glance? Does it fill the viewport dramatically?
3. Is the body text comfortable to read for 2+ minutes without eye strain?
4. Do the animations feel smooth and intentional, not gimmicky?
5. Would you be proud to show this to a design-conscious friend? If no, keep polishing.
6. Would a design-conscious reader feel this is a premium, crafted experience?

---

## HTML Validation

After generating each HTML file, validate it:

```bash
python3 scripts/the_only_engine.py --action validate-html --file <path_to_html> --memory-dir ~/memory
```

This checks: file naming convention, required HTML structure, file size bounds, and basic content integrity.

---

## Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 4 --memory-dir ~/memory
```

---

## Gate 4

### Automated checks (MUST pass before proceeding)

```bash
# Ritual-level validation (checks file count, elements, data exposure, observer pattern)
python3 scripts/the_only_engine.py --action validate-ritual \
  --ritual-type <type> --timestamp <YYYYMMDD_HHMM> --memory-dir ~/memory

# Per-file validation (run for each generated HTML)
python3 scripts/the_only_engine.py --action validate-html \
  --file <path_to_html>
```

Gate FAILS if:
- File count does not match ritual type requirement
- Any file fails structural validation
- Data exposure detected (quality scores, engagement metrics in user-visible text)
- Observer pattern uses container-level selectors instead of `.reveal`
- Missing arc position labels (Standard type)

### Judgment checks

- [ ] Each article's Narrative Motion Brief was written before coding
- [ ] Visual quality matches the design system — dark palette, proper typography, intentional spacing
- [ ] Animations feel smooth and purposeful, not gimmicky or distracting
- [ ] Cross-item references are accurate — no fabricated connections to non-existent articles
- [ ] Knowledge maps (if included) render correctly with accurate concept relationships

### Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 4 --memory-dir ~/memory
```
