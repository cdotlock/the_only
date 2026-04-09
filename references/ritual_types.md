# Adaptive Ritual Types

> **When to read**: Phase 0 (Pre-Flight), after loading memory and before deciding what kind of ritual to run. The ritual type determines **everything** — search strategy, synthesis depth, output format, and delivery style.

---

## 1. Why Adaptive Rituals

v1 had one format: "5 articles, push them." Every ritual looked the same regardless of what happened in the world, what the user needed, or where their understanding was.

v2 recognizes that learning isn't uniform. Sometimes you need breadth (what happened today?). Sometimes you need depth (explain this one thing thoroughly). Sometimes you need challenge (here's why you might be wrong). Sometimes you need connection (how does everything fit together?).

**The ritual type is selected automatically** based on signals from memory, the knowledge graph, and the current context. The user can also request a specific type.

---

## 2. Ritual Types

### Standard Ritual (default)

The classic 5-item curated delivery with narrative arc. Use when no special conditions are met.

| Attribute | Value |
|-----------|-------|
| Items | `items_per_ritual` (default 5) |
| Search queries | 8-15 |
| Depth | Moderate — 1-2 min read per item |
| Arc | Full 5-position narrative arc |
| When | Default. No override conditions triggered. |

### Deep Dive

A single topic explored from multiple angles. One long article instead of five short ones.

| Attribute | Value |
|-----------|-------|
| Items | 1 (long-form, 8-12 min read) |
| Search queries | 15-25 (all on the same topic) |
| Depth | Maximum — primary sources, historical context, opposing views, practical implications |
| Arc | Internal arc within the single piece: Context → Mechanism → Debate → Implications → Synthesis |
| When | (1) User requests it. (2) A storyline reaches 5+ rituals — time to consolidate. (3) A breakthrough development in a core interest area. |

**Structure of a Deep Dive article:**
1. **Context** — Why this matters now. Connect to what the user already knows (from the graph).
2. **Mechanism** — How it actually works, explained progressively. First principles up.
3. **Evidence** — Primary sources, data, expert positions. Evaluate conflicting claims.
4. **Debate** — Steel-man the opposing view. What could go wrong? Who disagrees and why?
5. **Implications** — What changes if this is true? What should the user do differently?
6. **Connections** — How does this connect to other concepts in the knowledge graph? Include a Mermaid diagram.
7. **Open Questions** — What we still don't know. Seed for future rituals.

### Debate

Two perspectives on a contested topic, presented fairly and then adjudicated.

| Attribute | Value |
|-----------|-------|
| Items | 2-3 (pro, con, synthesis) |
| Search queries | 10-15 (deliberately seeking opposing views) |
| Depth | High — must steel-man both sides |
| Arc | Thesis → Antithesis → Synthesis |
| When | (1) User requests it. (2) Knowledge graph detects a `contradicts` edge with high weight. (3) A topic in user's interests has active public controversy. |

**Rules:**
- Each position gets equal word count and quality of argument
- The synthesis doesn't "pick a winner" — it maps the decision space
- Include a "What would change your mind?" section for each side
- If Ruby has a position, she states it transparently as her own

### Tutorial

Teaches a concept the user hasn't mastered yet, building from zero to functional understanding.

| Attribute | Value |
|-----------|-------|
| Items | 1 (structured lesson, 5-8 min) |
| Search queries | 10-15 (seeking explanations, examples, analogies) |
| Depth | Progressive — starts simple, builds to expert-level |
| Arc | Intuition → Formal Definition → Worked Example → Edge Cases → Practice Questions |
| When | (1) User requests it. (2) Knowledge graph shows a concept at "introduced" mastery that connects to 3+ "understood" concepts — the user is ready to learn this. (3) A gap analysis reveals a critical missing concept. |

**Structure:**
1. **The Hook** — Why you should care about this (connect to something they already know)
2. **Intuition** — Explain it like you're at a whiteboard with a friend. Analogy first.
3. **Formal Definition** — Now the precise version. Jargon is allowed here because intuition is established.
4. **Worked Example** — Walk through a concrete case step by step.
5. **Edge Cases** — Where the intuition breaks down. What's surprising about this?
6. **Practice Questions** — 2-3 Socratic questions that test understanding (see Interactive Elements in webpage_design_guide.md)
7. **Knowledge Map** — Mermaid diagram showing where this concept sits in the graph

### Weekly Synthesis

A meta-ritual that looks back at the past week's content and finds the hidden connections.

| Attribute | Value |
|-----------|-------|
| Items | 1 (synthesis article, 5-8 min) |
| Search queries | 0-3 (mostly working from archive + graph) |
| Depth | Meta — pattern recognition, not new content |
| Arc | Recap → Hidden Connections → Evolving Storylines → Knowledge Map → Next Week's Questions |
| When | (1) Every 7th ritual (automatic). (2) User asks "what did I learn this week?" |

**Structure:**
1. **This Week's Thread** — What was the implicit theme across this week's rituals?
2. **Connections You Might Have Missed** — Cross-item links that weren't obvious in individual rituals
3. **Storyline Updates** — How each active storyline progressed
4. **Knowledge Growth** — What concepts moved up in mastery? What's new?
5. **Visual Map** — Mermaid diagram of this week's concept cluster
6. **Questions for Next Week** — What Ruby is curious about for upcoming rituals

### Flash Briefing

Ultra-short, high-density update. For when the user is busy but wants to stay current.

| Attribute | Value |
|-----------|-------|
| Items | 7-10 (one paragraph each, 30 seconds per item) |
| Search queries | 5-8 (broad, current) |
| Depth | Minimal — headline + one insight + why it matters |
| Arc | None — pure reverse-chronological or by importance |
| When | (1) User requests it ("quick brief", "just the headlines"). (2) Config `ritual_type_override: flash`. |

**Rules:**
- Each item: 2-3 sentences max. One core insight. One "so what."
- No narrative frills, no analogies, no cross-references
- All items in a single HTML file (exception to the one-article-per-file rule)
- Optimized for mobile reading

---

## 3. Automatic Type Selection

During Phase 0, after loading memory + graph, evaluate these conditions in order:

```
1. User explicitly requested a type? → Use that type.
2. Is this the 7th ritual since last Weekly Synthesis? → Weekly Synthesis.
3. Does any active storyline have ritual_count >= 5
   AND no Deep Dive has covered it? → Deep Dive on that storyline.
4. Does the knowledge graph have a `contradicts` edge
   with weight >= 3 between two core-interest concepts? → Debate.
5. Does gap analysis show a "critical" gap (high-severity,
   connected to 3+ mastered concepts)? → Tutorial on that gap.
6. Did user say "quick" / "busy" / "just headlines"? → Flash Briefing.
7. Default → Standard Ritual.
```

**Log the selection reason** in the Episodic entry: `"ritual_type": "deep_dive", "type_reason": "storyline 'AI reasoning' at 5 rituals"`

---

## 4. User Commands

| Command | Maps to |
|---------|---------|
| "deep dive into [topic]" | Deep Dive |
| "debate [topic]" / "both sides of [topic]" | Debate |
| "teach me [topic]" / "explain [topic]" | Tutorial |
| "weekly summary" / "what did I learn this week?" | Weekly Synthesis |
| "quick brief" / "just headlines" / "flash" | Flash Briefing |
| "run a ritual" / "deliver now" (default) | Auto-select per §3 |

---

## 5. Output Format Variations

| Type | Files | Approx Length | Special Elements |
|------|-------|---------------|-----------------|
| Standard | 5 HTML files | 1-2 min each | Narrative arc labels, "Previously on..." |
| Deep Dive | 1 HTML file | 8-12 min | Table of contents, knowledge map, section navigation |
| Debate | 2-3 HTML files | 3-5 min each | Side-by-side comparison, "What would change your mind?" |
| Tutorial | 1 HTML file | 5-8 min | Progressive disclosure, practice questions, knowledge map |
| Weekly Synthesis | 1 HTML file | 5-8 min | Storyline timeline, weekly knowledge graph |
| Flash Briefing | 1 HTML file | 3-5 min total | Compact cards, no animations |

All types except Flash Briefing follow the design system in `webpage_design_guide.md`. Flash Briefing uses a simplified mobile-first layout.
