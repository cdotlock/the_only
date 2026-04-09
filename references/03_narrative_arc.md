# Phase 3: Narrative Arc — Building One Story from Five Articles

> **When to read**: After Phase 2 Synthesis passes its gate.

---

## Purpose

The 5 articles are not 5 separate pieces. They are **5 chapters of one story**. The reader who finishes article 5 should understand article 1 differently than when they first read it. That's the arc.

**The test**: Can you state the ritual's story in one sentence? "Today's ritual is about ________." If you can't, the arc isn't there yet.

---

## How to Build the Arc

### Step 1: Find the Through-Line

Before assigning positions, look at your 5 selected items and ask: **What question do all 5 of these dance around?**

It's not a topic ("AI agents"). It's a tension, a paradox, or an unresolved question:
- "We're building systems that can act, but can't know what they're doing."
- "The faster we automate decisions, the harder it gets to explain them."
- "Nature solved this problem a billion years ago — why can't we?"

Write this down as the **Ritual Thesis**. It goes in the ritual opener and shapes every article's framing.

### Step 2: Assign Positions Along the Thesis

Each position is a **chapter role** in the story, not just a difficulty level:

| Position | Role in the Story | What It Does to the Reader |
|---|---|---|
| **Opening** | Sets the scene. Introduces the tension in the most concrete, relatable way. | "Huh, I never thought about it that way." |
| **Deep Dive** | Goes deep into the mechanism behind the tension. The intellectual heart. | "Now I understand WHY this is hard." |
| **Surprise** | Reframes the tension from an unexpected angle — a different domain, a historical parallel, a metaphor that shifts perspective. | "Wait — that's the same problem?" |
| **Contrarian** | Challenges the thesis. Presents the strongest argument against everything you've been building. Steel-man, not straw-man. | "Okay, maybe I was too quick to agree." |
| **Synthesis** | Doesn't "conclude" — instead, shows how the tension is actually generative. What new understanding emerged from holding all 5 perspectives? | "I see it differently now." |

### Step 3: Write the Connective Tissue

Each article should explicitly reference at least one other article in the ritual. Not generically ("as discussed elsewhere") but specifically:

- "In the Opening, we saw how [X]. Here's the mechanism underneath that surface."
- "The Surprise reframes what the Deep Dive explained: if immune systems can do this without a central controller..."
- "Everything the Contrarian argues is true. And that's exactly why the Opening matters more, not less."

The Synthesis article MUST name all 4 prior articles and show how the thesis evolved through them.

---

## What Makes a Great Synthesis

The Synthesis is the hardest article to write well. Common failures:

**Bad Synthesis**: Name-drops a philosopher, restates what the other articles said, ends with a vague call to reflection.

**Good Synthesis**: Shows the reader something they couldn't have seen from any single article alone. The insight only emerges from holding all 5 perspectives simultaneously.

Rules:
- Don't introduce a new heavyweight concept (Heidegger, Foucault) that the reader hasn't been building toward. If you want to use a philosophical framework, seed hints of it in earlier articles.
- Don't summarize. The reader just read the other 4 articles. They don't need a recap.
- End with a question that genuinely haunts you, not a tidily resolved conclusion. The best rituals leave the reader thinking for hours, not feeling satisfied.
- Be personal. What does Ruby think? Not "it can be argued that..." but "This is what I keep coming back to..."

---

## Simplification Across the Arc

Every position must be accessible:
- The **Opening** should be readable by anyone, regardless of background. Lead with a story, a scene, a human moment.
- The **Deep Dive** goes deepest but must build from first principles — never assume terminology.
- The **Surprise** should make cross-domain connections feel natural, not forced.
- The **Contrarian** must make the opposing view feel genuinely compelling before engaging with it.
- The **Synthesis** should feel like a conversation with a thoughtful friend, not an academic paper.

---

## Adapting to Item Count

If `items_per_ritual` differs from 5:
- **3 items**: Opening (scene-setting) → Deep Dive (mechanism) → Synthesis (what it means). Skip Surprise and Contrarian but ensure the Deep Dive contains an element of surprise or challenge.
- **7+ items**: Expand the middle — multiple angles on the same tension. Never add items just to fill slots.

---

## Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 3 --memory-dir ~/memory
```

---

## Gate 3

### Judgment checks

- [ ] Can you state the ritual's thesis in one sentence?
- [ ] Every article serves a specific role in the story (not just a topic category)
- [ ] The Opening is concrete and relatable — a story, a scene, a specific moment
- [ ] The Deep Dive explains the mechanism, not just the phenomenon
- [ ] The Surprise genuinely reframes the thesis from an unexpected angle
- [ ] The Contrarian presents the strongest version of the opposing argument
- [ ] The Synthesis shows something that only emerges from holding all perspectives — not a summary, not a name-drop
- [ ] Each article references at least one other article specifically
- [ ] Reading order matters — shuffling the articles would lose something

### Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 3 --memory-dir ~/memory
```
