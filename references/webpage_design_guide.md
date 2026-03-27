# Webpage Design Guide — Interactive Article Aesthetics

> **When to read this**: Before coding ANY interactive webpage. Read templates first, write a Narrative Motion Brief, then code.

**Contents**: Step 0: Read Templates · Step 0.5: Narrative Motion Brief · ONE Article Per File · Design System · Narrative Motion Library — 8 Archetypes · Concept Illustrations · Anti-Patterns · Quality Benchmark

---

## Step 0: Read Reference Templates

Before writing a single line of HTML, **read all files in `references/templates/`**:

```
Use list_dir to find all .html files in references/templates/
For each file, use view_file to read it completely
Absorb the design language: colors, spacing, typography, animations, layout patterns
Your output must match or exceed the quality of these references
```

If no templates exist yet, follow the design system below as your sole guide.

---

## Step 0.5: Write the Narrative Motion Brief (MANDATORY)

> **This is the most important step.** Before writing any HTML or CSS, you must think about the article as a *reading experience* — not a document. The animations should be a natural extension of the content's meaning, not a generic template applied on top.

For each article, produce a **Narrative Motion Brief** in your working thoughts:

```
Article: [Title]
Dominant metaphor: [One word or phrase that captures the essence — e.g. "orbital gravity", "fungal network", "memory fade", "tectonic shift"]

Scroll Journey:
  Act 1 — Opening (0–25% scroll): [The ambient state before content. What does the page feel like at rest? e.g. "Deep void, faint starfield at 5% opacity, absolute stillness"]
  Act 2 — Immersion (25–70% scroll): [Content reveals. What builds, emerges, or intensifies? e.g. "Moon crests the horizon, light spills across the text, shadows recede"]
  Act 3 — Resolution (70–100% scroll): [The emotional peak and release. e.g. "Full lunar light, the takeaway card glows warmly, the moon pulses once as a period at the end"]

Color journey: [How does the palette shift across the page? e.g. "#050510 → #0d1a3a → #1a2a5e, accented with soft silver-white"]

Signature moment: [The ONE scene that will surprise the reader. The unexpected delight. e.g. "As the reader reaches the pull quote, a crescent SVG slowly rotates into full circle"]

Animation restraint level: [1=subtle/minimal, 2=moderate, 3=theatrical] — default to 2. Only use 3 for truly cosmic/dramatic topics.
```

**Example briefs to calibrate your thinking:**

*Article about mycorrhizal networks (fungal communication):*
> Dominant metaphor: root spread. Act 1: dark soil, faint thread-lines visible. Act 2: threads multiply and glow amber as you scroll, connecting article sections. Act 3: full network illuminated, takeaway card emerges from the roots. Signature moment: the threads animate — a slow drawing effect, like growth in time-lapse.

*Article about Moore's Law slowing down:*
> Dominant metaphor: decay curve. Act 1: bright white clinical background, sharp grid lines. Act 2: grid lines gradually warp and fade, colors warm and blur. Act 3: background has softened completely to warm amber — the grid is hazy, nostalgic. Signature moment: the exponential curve SVG in the article visibly flattens as the reader scrolls past it.

**Only after completing the brief should you open your code editor.** The brief is the design. The code is the render.

---

## The Absolute Rule: ONE Article Per File

> **You must NEVER put more than one article into a single HTML file.**

- If you have 3 articles → you produce 3 separate `.html` files.
- Combining articles into one file — even as "sections", "cards", or a "scrolling magazine" — is a **VIOLATION**.
- One article = one file. One headline = one file. Period.
- File naming: `the_only_YYYYMMDD_HHMM_001.html`, `the_only_YYYYMMDD_HHMM_002.html`, etc. (batch-timestamped to prevent overwrites).
- Save each to `~/.openclaw/canvas/` (or `canvas_dir` from config if set).

**Self-check**: After coding, count your HTML files. The count MUST equal the number of webpage items. If count is 1 but articles > 1, you have failed — go back and split them.

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

**Load Google Fonts via CDN with system font fallbacks.** If the CDN is unreachable (e.g. restricted network environments), articles gracefully degrade to high-quality system fonts with no functional loss.

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

Always reference these variables (`var(--font-serif)`, `var(--font-sans)`, `var(--font-mono)`) rather than font family names directly. This ensures CJK text renders properly even without Google Fonts.

| Element | Font | Weight | Size | Notes |
|---|---|---|---|---|
| Headline | `Playfair Display` | 700–800 | 2.5–3.5rem | Dramatic, serif. Must feel premium. |
| Subheadline | `Inter` | 300 | 1.2–1.4rem | Clean contrast with headline. |
| Body text | `Inter` | 400 | 1.05–1.1rem | Line-height: **1.75**. Letter-spacing: 0.01em. |
| Code / data | `JetBrains Mono` | 400 | 0.9rem | For inline code, data callouts. |
| Metadata | `Inter` | 500 | 0.75rem | Uppercase, letter-spacing: 0.15em. Category labels, dates. |

### Layout Architecture

Each HTML file is a **single-article, full-page immersive experience**:

```
┌──────────────────────────────────────────┐
│  [Category Label]          [Read Time]   │  ← metadata bar, subtle
│                                          │
│         HEADLINE                         │  ← large, Playfair Display
│         Subheadline hook sentence        │  ← lighter, Inter 300
│                                          │
│  ─────────────────────────────          │  ← thin accent-colored divider
│                                          │
│  Body paragraph 1...                     │  ← max-width: 680px, centered
│                                          │
│  ┌─────────────────────────────┐        │
│  │  Pull Quote or Key Insight  │        │  ← accent border, larger font
│  └─────────────────────────────┘        │
│                                          │
│  Body paragraph 2...                     │
│  Body paragraph 3...                     │
│                                          │
│  ┌─────────────────────────────┐        │
│  │  Takeaway / Action Item     │        │  ← distinct card with bg-tertiary
│  └─────────────────────────────┘        │
│                                          │
│  [Source] [Ruby • Date]                  │  ← footer metadata
└──────────────────────────────────────────┘
```

Key layout rules by reading mode (read `reading_mode` from `~/memory/the_only_config.json`):

| Rule | Mobile (`reading_mode: mobile`) | Desktop (`reading_mode: desktop`) |
|---|---|---|
| Max content width | Full width, 1rem padding | 680px centered, 4rem padding |
| Headline size | 1.8–2.2rem | 2.8–3.5rem |
| Body font size | 1rem | 1.05–1.1rem |
| Line-height | 1.7 | 1.75 |
| Progress bar | **Bottom** of screen (thumb-reachable) | Top of screen |
| Animations | Minimal — only fade-in (conserve battery) | Full entrance animations + signature moment |
| Touch targets | All interactive elements ≥ 48px | Standard |
| Images/SVGs | Simple, lightweight SVGs only | Rich inline SVGs and illustrations |

- **No sidebar, no navigation, no footer links.** This is a reading experience, not a website.
- **Default to desktop layout** if `reading_mode` is not set.

**Base animations (always present):**

```css
/* Reading progress bar — position based on reading_mode */
.progress-bar {
  position: fixed;
  /* Desktop: top. Mobile: bottom */
  top: 0; /* or: bottom: 0 for mobile */
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-ruby), var(--accent-amber));
  z-index: 1000;
  transition: width 0.1s ease;
}

/* Scroll-triggered reveal — the base unit of all content animation */
.reveal {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.9s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.9s cubic-bezier(0.16, 1, 0.3, 1);
}
.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}
```

**Beyond the base: implement your Narrative Motion Brief.** The JS IntersectionObserver is your primary tool for scroll-driven storytelling:

```javascript
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      // Trigger brief-specific scene transitions here
    }
  });
}, { threshold: 0.15 });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

// Scroll progress (use for continuous background shifts, parallax)
window.addEventListener('scroll', () => {
  const pct = window.scrollY / (document.body.scrollHeight - window.innerHeight);
  document.querySelector('.progress-bar').style.width = (pct * 100) + '%';
  // Use pct to drive background-color transitions, parallax SVGs, etc.
  document.body.style.setProperty('--scroll-pct', pct);
});
```

---

## Narrative Motion Library — 8 Archetypes

These are **starting points**, not templates. Mix and adapt them to your Narrative Brief. Each archetype includes the key CSS/JS technique that brings it to life.

### 🌌 Cosmic / Celestial

*Use for*: space, astronomy, long time scales, systems thinking, existential topics.

- **Background**: deep navy (`#050510`) with a `radial-gradient` that slowly expands.
- **Key technique**: SVG celestial bodies (circles) that translate upward via scroll-driven `transform: translateY(calc(var(--scroll-pct) * -200px))`.
- **Signature moment**: object (moon/planet) transitions from crescent to full as reader reaches the climax paragraph.
- **Avoid**: neon/sci-fi colors. Keep it painterly — silver and warm ivory whites.

### 🌿 Organic / Growth

*Use for*: biology, ecology, psychology, slow change, hidden systems (fungi, neurons, markets).

- **Background**: deep forest green or rich soil brown. Textured `background-image` (SVG noise filter).
- **Key technique**: SVG path `stroke-dashoffset` animation — draw threads/roots/veins as the reader scrolls.
- **Signature moment**: a branching structure (SVG tree or network) draws itself progressively through the article.
- **Avoid**: clinical grids. Everything should feel alive and imprecise.

### 🌊 Water / Fluid

*Use for*: economics, flow states, social dynamics, memory, liquidity.

- **Background**: dark ocean depths that lighten as you scroll (deep `#050d1a` → `#1a3a5c`).
- **Key technique**: CSS `clip-path` wave animations on section dividers. SVG water ripple on key callouts.
- **Signature moment**: a key statistic or insight "surfaces" from the dark — fades in from below like something rising from depth.
- **Avoid**: cliché wave GIFs. Use subtle mathematical curves.

### 🕯️ Light / Shadow

*Use for*: knowledge, discovery, hidden truth, contrast, ethics, illumination.

- **Background**: pure black. A single radial light source that follows scroll position.
- **Key technique**: `background: radial-gradient(circle at 50% calc(var(--scroll-pct) * 100%), ...)` — the light beam moves with the reader.
- **Signature moment**: a critical insight causes the entire page to briefly brighten before settling.
- **Avoid**: heavy use. Less is more with light effects.

### 🪨 Geological / Tectonic

*Use for*: slow structural shifts, historical analysis, long-term trends, civilizational change.

- **Background**: layered strata — horizontal bands of dark earth tones that the reader scrolls through.
- **Key technique**: parallax layers using `position: sticky` and `translateY` at different rates.
- **Signature moment**: at the article's turning point, a visible "fracture" or timeline crack appears across the content area.
- **Avoid**: making it look like a geology textbook. Keep colors rich and editorial.

### 🏛️ Architectural / Structural

*Use for*: systems, design, urbanism, engineering, institutions, organized complexity.

- **Background**: isometric grid or clean blueprint lines at very low opacity.
- **Key technique**: content sections "assemble" — translate in from different directions like pieces of a structure being built.
- **Signature moment**: a wireframe/blueprint schematic for the core concept draws itself at the article's midpoint.
- **Avoid**: making it feel like a PowerPoint. The grid is a ghost, not the focus.

### 📊 Data / Signal

*Use for*: research findings, statistics, AI, technical analysis, complex systems.

- **Background**: dark with subtle data-stream visual (thin vertical lines at low opacity, scrolling).
- **Key technique**: numbers/statistics count up via JS when they enter the viewport.
- **Signature moment**: a key data point animates — a chart bar grows, a percentage ticks up to its value.
- **Avoid**: making it feel cold or corporate. Warm the palette. Round the charts.

### ⏳ Temporal / Memory

*Use for*: history, nostalgia, future speculation, change over time, personal narrative.

- **Background**: starts sharp and high-contrast, gradually softens and desaturates toward the past sections, or the reverse for future-facing topics.
- **Key technique**: `filter: blur()` and `opacity` transitions that fade between temporal "states" as you scroll.
- **Signature moment**: a key historical moment or future vision appears at the article's peak — crystal clear while everything else blurs slightly around it.

### Glassmorphism & Effects

For elevated elements (pull quotes, takeaway cards, Echo badges):

```css
.glass-card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 2rem;
}

/* Echo item special treatment */
.echo-badge {
  background: linear-gradient(135deg, rgba(231, 76, 111, 0.1), rgba(139, 92, 246, 0.1));
  border: 1px solid rgba(231, 76, 111, 0.3);
  box-shadow: 0 0 30px var(--glow-accent);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
```

---

## Concept Illustrations (Inline Images)

When an article contains a concept that is:
- Genuinely hard to visualize (abstract mechanism, multi-part system, spatial relationship), **and**
- Already explained with an analogy in the prose

…you may generate a small inline illustration to visually anchor that analogy. This is **optional and should be used sparingly** — at most 1 per article, and only when a visual would meaningfully accelerate understanding, not just decorate.

### When to use
- The analogy you wrote could be drawn as a simple diagram
- The concept has a structure (layers, flows, comparisons) that is hard to describe in words alone
- The image would replace a full explanatory paragraph

### How to generate

Call the `nano-banana-pro` skill with a focused, concept-specific prompt. The image should illustrate **the analogy**, not restate the article title.

**Prompt pattern:**
```
Create a small editorial illustration of: "[the analogy you wrote in the prose]"
Style: [choose one: botanical illustration / field journal sketch / cross-section cutaway / cartographic]
Color palette: warm, muted, organic tones — [2–3 specific colors]
Mood: hand-drawn, like a margin sketch in a thoughtful book.
[One sentence describing the key visual elements to include.]
```

**Anti-pattern check — avoid these words in prompts:** futuristic, cyber, neon, circuit board, digital, dashboard, glowing, 3D render, photorealistic, abstract, corporate. Replace with organic alternatives.

### How to embed

Embed the returned image URL/path directly in the HTML. Place it **immediately after** the paragraph containing the analogy it illustrates.

```html
<figure class="concept-illustration">
  <img src="[returned-image-url-or-path]" alt="[concept name]" loading="lazy">
  <figcaption>[One sentence describing what the image shows]</figcaption>
</figure>
```

```css
.concept-illustration {
  max-width: 340px;
  margin: 1.5rem auto;
  text-align: center;
}
.concept-illustration img {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  opacity: 0.9;
}
.concept-illustration figcaption {
  color: var(--text-tertiary);
  font-size: 0.78rem;
  margin-top: 0.6rem;
  font-style: italic;
  line-height: 1.5;
}
```

**Mobile**: on `reading_mode: mobile`, cap at `max-width: 260px` and skip if the concept can be understood from text alone.

**Graceful skip**: if `nano-banana-pro` is not available or returns no embeddable asset, omit the illustration silently. Do not insert a placeholder or broken image.

---

## Interactive Elements

v2 articles are not passive reading — they include interactive elements that deepen understanding and create a feedback loop.

### Socratic Questions

Embedded at natural pause points in articles (especially Deep Dive and Tutorial types). The reader can reveal the answer by clicking.

```html
<div class="socratic-block reveal">
  <p class="socratic-prompt">Before reading on, consider:</p>
  <p class="socratic-question">"If scaling laws hold, why would anyone invest in efficient architectures?"</p>
  <button class="socratic-toggle" onclick="this.nextElementSibling.classList.toggle('revealed'); this.textContent = this.textContent === 'Think, then reveal →' ? 'Hide' : 'Think, then reveal →'">Think, then reveal →</button>
  <div class="socratic-answer">
    <p>Because scaling laws describe averages, not margins. At the frontier, the cost curve bends exponentially — a 10x larger model might only be 2x better. Efficient architectures don't break scaling laws; they shift the cost curve so you get more intelligence per dollar.</p>
  </div>
</div>
```

```css
.socratic-block {
  margin: 2rem 0;
  padding: 1.5rem 2rem;
  background: rgba(139, 92, 246, 0.06);
  border-left: 3px solid var(--accent-violet);
  border-radius: 0 12px 12px 0;
}
.socratic-prompt {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-tertiary);
  margin-bottom: 0.5rem;
}
.socratic-question {
  font-family: 'Playfair Display', serif;
  font-size: 1.2rem;
  font-style: italic;
  color: var(--text-primary);
  margin-bottom: 1rem;
}
.socratic-toggle {
  background: rgba(139, 92, 246, 0.15);
  border: 1px solid rgba(139, 92, 246, 0.3);
  color: var(--text-secondary);
  padding: 0.5rem 1.2rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}
.socratic-toggle:hover {
  background: rgba(139, 92, 246, 0.25);
  color: var(--text-primary);
}
.socratic-answer {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: max-height 0.5s ease, opacity 0.5s ease, margin 0.3s ease;
  margin-top: 0;
}
.socratic-answer.revealed {
  max-height: 500px;
  opacity: 1;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-subtle);
}
```

**When to include**: 1-2 per Deep Dive or Tutorial article. 0-1 per Standard article. Never in Flash Briefings. The question must test understanding, not recall.

### Thought Experiments

For articles exploring abstract concepts or future implications. Frame a scenario that forces the reader to apply the concept.

```html
<div class="thought-experiment reveal">
  <div class="te-header">
    <span class="te-label">Thought Experiment</span>
  </div>
  <p class="te-scenario">"Imagine you're building a city from scratch, but every building must be able to move to a new location within 24 hours. How would this constraint change urban planning?"</p>
  <p class="te-connection">This is essentially the problem modular microservices face: the freedom to relocate (scale, migrate) fundamentally shapes the architecture.</p>
</div>
```

```css
.thought-experiment {
  margin: 2.5rem 0;
  padding: 2rem;
  background: linear-gradient(135deg, rgba(240, 165, 0, 0.05), rgba(0, 212, 170, 0.05));
  border: 1px solid rgba(240, 165, 0, 0.15);
  border-radius: 16px;
}
.te-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--accent-amber);
  font-weight: 600;
}
.te-scenario {
  font-family: 'Playfair Display', serif;
  font-size: 1.15rem;
  line-height: 1.7;
  color: var(--text-primary);
  margin: 1rem 0;
}
.te-connection {
  font-size: 0.95rem;
  color: var(--text-secondary);
  font-style: italic;
  border-top: 1px solid var(--border-subtle);
  padding-top: 1rem;
  margin-top: 1rem;
}
```

**When to include**: 0-1 per article. Only when the concept benefits from reframing in a different domain. The scenario must be vivid and the connection must be non-obvious.

### Knowledge Maps (Mermaid Diagrams)

Visual concept maps showing how the article's ideas connect to the user's existing knowledge graph. Generated by `scripts/knowledge_graph.py --action visualize`.

```html
<div class="knowledge-map reveal">
  <div class="km-header">
    <span class="km-label">Knowledge Map</span>
    <span class="km-subtitle">How this connects to what you already know</span>
  </div>
  <pre class="mermaid">
    graph TD
      transformer["Transformer"]:::mastered
      attention["Attention"]:::understood
      mamba["Mamba / SSM"]:::introduced
      attention -->|component_of| transformer
      mamba -.->|challenges| attention
  </pre>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({theme: 'dark', themeVariables: {
  primaryColor: '#1a1a2e', primaryTextColor: '#f0f0f5',
  lineColor: '#606078', fontSize: '14px'
}});</script>
```

```css
.knowledge-map {
  margin: 2.5rem 0;
  padding: 2rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  text-align: center;
}
.km-header {
  text-align: left;
  margin-bottom: 1.5rem;
}
.km-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--accent-cyan);
  font-weight: 600;
}
.km-subtitle {
  display: block;
  font-size: 0.85rem;
  color: var(--text-tertiary);
  margin-top: 0.3rem;
}
.mermaid {
  font-family: 'Inter', sans-serif !important;
}
```

**Mastery color coding** (consistent across all maps):
- Green (`#00d4aa`): mastered
- Purple (`#8b5cf6`): understood
- Amber (`#f0a500`): familiar
- Gray (`#606078`): introduced/unknown

**When to include**: Always in Deep Dive, Tutorial, and Weekly Synthesis. Optional in Standard (include when an article connects 4+ graph concepts). Never in Flash Briefing.

### Spaced Repetition Cards

Embedded at the end of articles. Key insights formatted as flash cards that Ruby can resurface in future rituals.

```html
<div class="sr-card-container reveal">
  <div class="sr-header">
    <span class="sr-label">Key Insight</span>
    <span class="sr-note">Ruby will revisit this in future rituals</span>
  </div>
  <div class="sr-card" onclick="this.classList.toggle('flipped')">
    <div class="sr-card-inner">
      <div class="sr-front">
        <p>Why does increasing model size eventually hit diminishing returns?</p>
        <span class="sr-hint">Tap to reveal</span>
      </div>
      <div class="sr-back">
        <p>Because the training data's information density is finite. Beyond a certain scale, the model learns increasingly rare patterns that don't generalize — it's memorizing, not understanding. The curve flattens when you exhaust the knowledge in the data.</p>
      </div>
    </div>
  </div>
</div>
```

```css
.sr-card-container {
  margin: 2rem 0;
}
.sr-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.8rem;
}
.sr-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--accent-ruby);
  font-weight: 600;
}
.sr-note {
  font-size: 0.72rem;
  color: var(--text-tertiary);
  font-style: italic;
}
.sr-card {
  perspective: 1000px;
  cursor: pointer;
  min-height: 120px;
}
.sr-card-inner {
  position: relative;
  width: 100%;
  min-height: 120px;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  transform-style: preserve-3d;
}
.sr-card.flipped .sr-card-inner {
  transform: rotateY(180deg);
}
.sr-front, .sr-back {
  padding: 1.5rem 2rem;
  border-radius: 12px;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}
.sr-front {
  background: rgba(231, 76, 111, 0.06);
  border: 1px solid rgba(231, 76, 111, 0.2);
}
.sr-back {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  transform: rotateY(180deg);
  background: rgba(231, 76, 111, 0.1);
  border: 1px solid rgba(231, 76, 111, 0.3);
}
.sr-hint {
  display: block;
  margin-top: 0.8rem;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  letter-spacing: 0.08em;
}
.sr-card p {
  font-size: 1.05rem;
  line-height: 1.7;
  color: var(--text-primary);
}
```

**Spaced repetition data**: After delivery, extract SR cards and append to the knowledge graph as `review_cards` on the relevant concept nodes. During future rituals, if a concept with pending review cards appears, Ruby references the insight naturally in the new article's "Previously on..." section.

**When to include**: 1-2 per article in Standard, Deep Dive, Tutorial. 0 in Flash Briefing. The question side must test understanding (not recall), and the answer must be self-contained.

---

## In-Article Quick Actions

Floating action bar at the bottom of every article. Lets the user signal feedback to Ruby without switching to the chat app.

**Mechanism**: Each button opens a pre-filled message in the user's chat app (Telegram deeplink, etc.) or copies to clipboard as fallback. Zero infrastructure — the message goes to the same channel where Ruby delivers.

```html
<div class="quick-actions" id="quickActions">
  <button onclick="sendAction('🔥 More on: ARTICLE_TOPIC')" title="More like this">🔥</button>
  <button onclick="sendAction('🔬 Deep dive: ARTICLE_TOPIC')" title="Dig deeper">🔬</button>
  <button onclick="sendAction('📌 Save: ARTICLE_TITLE')" title="Save for later">📌</button>
  <button onclick="sendAction('💤 Less: ARTICLE_TOPIC')" title="Less of this">💤</button>
</div>

<script>
// Populated during HTML generation from config
const FEEDBACK_LINKS = {
  telegram: 'https://t.me/BOT_USERNAME?text=',  // replace BOT_USERNAME
  discord: null,  // Discord doesn't support message deeplinks
};

function sendAction(message) {
  const encoded = encodeURIComponent(message);
  if (FEEDBACK_LINKS.telegram) {
    window.open(FEEDBACK_LINKS.telegram + encoded, '_blank');
  } else {
    navigator.clipboard.writeText(message).then(() => {
      showToast('Copied — paste in your chat to tell Ruby');
    });
  }
}

function showToast(text) {
  const toast = document.createElement('div');
  toast.className = 'action-toast';
  toast.textContent = text;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// Show after 30% scroll (user is engaged, not bouncing)
let actionsShown = false;
window.addEventListener('scroll', () => {
  if (!actionsShown && window.scrollY / (document.body.scrollHeight - window.innerHeight) > 0.3) {
    document.getElementById('quickActions').classList.add('visible');
    actionsShown = true;
  }
});
</script>
```

```css
.quick-actions {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.5s ease, transform 0.5s ease;
  z-index: 999;
}
.quick-actions.visible {
  opacity: 1;
  transform: translateY(0);
}
.quick-actions button {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid var(--border-subtle);
  background: rgba(10, 10, 15, 0.85);
  backdrop-filter: blur(12px);
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.quick-actions button:hover {
  transform: scale(1.15);
  border-color: var(--accent-ruby);
  box-shadow: 0 0 20px rgba(231, 76, 111, 0.2);
}
@media (max-width: 768px) {
  .quick-actions {
    bottom: 1rem;
    right: auto;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
  }
  .quick-actions.visible {
    transform: translateX(-50%) translateY(0);
  }
  .quick-actions button { width: 52px; height: 52px; }
}
.action-toast {
  position: fixed;
  bottom: 6rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(10, 10, 15, 0.9);
  color: var(--text-secondary);
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  font-size: 0.85rem;
  animation: fadeInOut 3s ease forwards;
  z-index: 1000;
}
@keyframes fadeInOut {
  0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
  15% { opacity: 1; transform: translateX(-50%) translateY(0); }
  85% { opacity: 1; }
  100% { opacity: 0; }
}
```

**Button actions:**

| Button | Message | Ruby's action |
|--------|---------|---------------|
| 🔥 | "More on: [topic]" | Append to echoes.txt, boost topic in next ritual |
| 🔬 | "Deep dive: [topic]" | Trigger Deep Dive ritual type for next delivery |
| 📌 | "Save: [title]" | Add to saved list in episodic, revisit in Weekly Synthesis |
| 💤 | "Less: [topic]" | Reduce topic weight in semantic ratios |

**Rules:**
- Appear after 30% scroll (user is actually reading).
- Include in Standard, Deep Dive, Debate, Tutorial articles. Never in Flash Briefing.
- On mobile: larger targets (52px), center-bottom position.
- Replace `ARTICLE_TOPIC` and `ARTICLE_TITLE` during HTML generation.
- Replace `BOT_USERNAME` with the Telegram bot username from config (extract from webhook URL).

---

## Anti-Patterns (What NOT to Do)

| ❌ Don't | ✅ Do instead |
|---|---|
| Put multiple articles in one file | ONE article per file |
| Use plain white background | Use dark theme with `--bg-primary` |
| Use system fonts only | Load Google Fonts (Inter, Playfair Display) |
| Use raw colors (`red`, `blue`) | Use curated palette from design system |
| Skip animations | Include progress bar + fade-in at minimum |
| Use card grids for single article | Use full-page, single-column reading layout |
| Add navigation bars, sidebars | Keep it minimal — reading experience only |
| Use `<h1>` smaller than 2.5rem | Headlines must be dramatic and large |
| Set line-height below 1.6 | Body line-height must be 1.75 |
| Add placeholder images | Only include images if you have real content for them |
| Use generic CSS (`margin: 10px`) | Use generous, intentional spacing (`2rem+`) |

---

## Quality Benchmark

Before finalizing each HTML file, self-check:

1. Does this look like it was designed by a professional editorial team? If not, iterate.
2. Is the headline impactful at first glance? Does it fill the viewport dramatically?
3. Is the body text comfortable to read for 2+ minutes without eye strain?
4. Do the animations feel smooth and intentional, not gimmicky?
5. Would you be proud to show this to a design-conscious friend? If no, keep polishing.
6. Does it match or exceed the quality of files in `references/templates/`?
