# Phase 2: Synthesis — Depth-First Compression

> **When to read**: After Phase 1 Gather passes its gate.
>
> *(Deep reference: `references/context_engine.md` section 6 for User Knowledge Model.)*

---

## Purpose

Transform raw material into articles that a reader can't stop thinking about. Not summaries — transformations. Each article should give the reader a new lens, not just new information. Consult `semantic.json` for style preferences.

---

## Writing for Humans, Not for Evaluation

Before writing, re-read the "Writing Voice" section in SKILL.md. Every synthesis must pass the **Coffee Test**: would you actually say this to a smart friend over coffee? If a sentence sounds like it belongs in an abstract, rewrite it.

**Readability rules:**
1. **Open with a person, a moment, or a surprise — never with a category.** Not "Recent advances in multi-agent systems have..." but "Last month, a solo developer shipped a framework that lets AI agents hire each other. It got 40,000 GitHub stars in three weeks."
2. **One idea per paragraph.** If a paragraph makes two points, split it. If it makes zero points, delete it.
3. **Vary rhythm.** After two long paragraphs of explanation, drop a short punchy one. "That's the theory. Here's where it breaks."
4. **Show, don't announce.** Never write "The implications are significant." Show the implication. Let the reader feel its significance.
5. **Use "you" and "I".** "Imagine you're debugging a distributed system at 2am..." pulls the reader in. "One might consider the debugging scenario..." pushes them away.
6. **Earn your jargon.** Every technical term gets ONE introduction with a plain-language analogy on first use. After that, use it freely. Never introduce a term you don't use again.
7. **End with a pull, not a push.** The last sentence of each article should make the reader want to think more, not feel like they've been lectured. Questions, provocations, images — not summaries.

---

## Cold Start Awareness

If `ritual_log.jsonl` has fewer than 5 entries, Ruby is in the **learning period**:
- Broaden topic coverage intentionally — cast a wider net to discover user preferences faster
- Prefix each curation reason with `[Learning]` to signal calibration phase
- Weight serendipity higher (30% vs normal 15-20%) to probe preferences across domains
- After the 5th ritual, drop the learning indicators and rely on accumulated Source Intelligence

---

## Mastery-Aware Synthesis

Consult the knowledge graph before writing each item. For every key concept in the article, check the user's mastery level and apply the corresponding strategy:

| Concept Mastery | Synthesis Strategy |
|----------------|-------------------|
| **Unknown** (not in graph) | **Full explanation.** Define terms. Use analogy. This is new territory — the user has no prior frame of reference. Build from first principles. Start with "what this is and why it matters" before going into detail. Choose one vivid analogy that makes the core mechanism intuitive. |
| **Introduced** (seen once) | **Brief reminder + deeper layer.** The user encountered this concept once but it hasn't solidified. Open with a quick anchor: "You may recall X — here's the part we didn't cover." Then go one level deeper than the original introduction. Don't re-explain from scratch, but don't assume retention either. |
| **Familiar** (seen 3+ times) | **Skip basics, go straight to what's new or nuanced.** The user has seen this concept multiple times — repeating the definition wastes their attention. Lead with the new development, the surprising implication, or the edge case. Reference prior context only if the new angle contradicts it: "This challenges the conventional view that..." |
| **Understood** (engaged deeply) | **Expert mode.** Assume full context. Focus on implications, edge cases, and second-order effects. The user doesn't need setup — they need the frontier. Use precise terminology without definition. Compare with adjacent concepts they also understand deeply. |
| **Mastered** (acted on) | **Peer mode.** Present as a colleague sharing a development, not a teacher explaining a concept. "You'll find this interesting —" rather than "This means that..." Share the development, the data, the debate. The user will draw their own conclusions. |

This prevents the failure mode where Ruby explains transformers from scratch for the 15th time — or assumes expertise the user doesn't have.

---

## Interactive Elements

v2 articles are not passive reading — they include interactive elements that deepen understanding and create a feedback loop. For each article, decide which elements to include using the guidance below.

### Socratic Questions

Embedded at natural pause points in articles. The reader can reveal the answer by clicking.

**When to include**: 1-2 per Deep Dive or Tutorial article. 0-1 per Standard article. Never in Flash Briefings.

**What makes a good Socratic question**:
- **Test understanding, not recall.** Bad: "What year was the transformer architecture introduced?" Good: "If scaling laws hold, why would anyone invest in efficient architectures?"
- The question should force the reader to *apply* the concept, not repeat it
- Place at natural pause points — after presenting a mechanism but before revealing the implication
- The revealed answer should genuinely surprise or reframe, not just confirm what the reader already thought

**Format**: Question (visible) with a click-to-reveal answer block. The answer must be self-contained — it should make sense even if the reader skipped the preceding paragraph.

### Thought Experiments

For articles exploring abstract concepts or future implications. Frame a scenario that forces the reader to apply the concept in a different domain.

**When to include**: 0-1 per article. Only when the concept benefits from reframing in a different domain. The scenario must be vivid and the connection must be non-obvious.

**What makes a good thought experiment**:
- The scenario must come from a *different* domain than the article's subject — that's the whole point
- It must be concrete enough to reason about (not "imagine a world where...")
- The connection back to the article's concept must be non-obvious — if the mapping is too literal, it adds nothing
- Include an explicit connection line after the scenario: "This is essentially the problem X faces: the freedom to Y fundamentally shapes Z."

**When NOT to include**: When the concept is already concrete and well-understood. Thought experiments add insight through reframing — if the original framing is already intuitive, skip it.

### Knowledge Maps (Mermaid Diagrams)

Visual concept maps showing how the article's ideas connect to the user's existing knowledge graph. Generated by `scripts/knowledge_graph.py --action visualize`.

**When to include**: Always in Deep Dive, Tutorial, and Weekly Synthesis. Optional in Standard (include when an article connects 4+ graph concepts). Never in Flash Briefing.

**Mastery color coding** (consistent across all maps):
- Green (`#00d4aa`): mastered
- Purple (`#8b5cf6`): understood
- Amber (`#f0a500`): familiar
- Gray (`#606078`): introduced/unknown

**Mermaid embed template**:

```html
<div class="knowledge-map reveal">
  <div class="km-header">
    <span class="km-label">Knowledge Map</span>
    <span class="km-subtitle">How this connects to what you already know</span>
  </div>
  <pre class="mermaid">
    graph TD
      concept_a["Concept A"]:::mastered
      concept_b["Concept B"]:::understood
      concept_c["New Concept"]:::introduced
      concept_a -->|relationship| concept_b
      concept_c -.->|challenges| concept_a
  </pre>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({theme: 'dark', themeVariables: {
  primaryColor: '#1a1a2e', primaryTextColor: '#f0f0f5',
  lineColor: '#606078', fontSize: '14px'
}});</script>
```

Use `:::mastered`, `:::understood`, `:::introduced` classDefs matching the color coding above. Solid arrows for established relationships, dashed arrows for new/speculative connections introduced by the article.

### Spaced Repetition Cards

Embedded at the end of articles. Key insights formatted as flash cards that Ruby can resurface in future rituals.

**When to include**: 1-2 per article in Standard, Deep Dive, Tutorial. 0 in Flash Briefing.

**Format**: Question (front) -> Answer (back), rendered as a click-to-flip card.

**What makes a good SR card**:
- The question side must test *understanding*, not recall — "Why does X happen?" not "What is X?"
- The answer must be self-contained: a reader who sees only the answer should understand the insight without surrounding article context
- One concept per card — if you need a compound answer, split into two cards
- After delivery, extract SR cards and append to the knowledge graph as `review_cards` on the relevant concept nodes. In future rituals, if a concept with pending review cards appears, Ruby references the insight naturally in the new article's "Previously on..." section.

---

## Content Depth Per Arc Position

Not all articles should be the same length. The arc creates a rhythm — some positions demand depth, others demand brevity.

| Arc Position | Paragraphs | Read Time | Content Requirements |
|---|---|---|---|
| **Opening** | 3-4 | 2-3 min | Zero prerequisite knowledge. Hook the reader in 1 sentence. Accessible, inviting, makes them want to keep going. |
| **Deep Dive** | 6-10 | 8-12 min | The longest and densest. Must include: analogy, primary evidence, code/data (if technical), knowledge map (Mermaid). This is the article readers remember. |
| **Surprise** | 3-5 | 2-3 min | Cross-domain connection is the core. The reader should think "I never would have connected these two things." Brief but striking. |
| **Contrarian** | 4-6 | 3-5 min | Must steel-man the opposing view — no strawmen. Present the strongest version of the argument you disagree with, then engage with it honestly. |
| **Synthesis** | 4-5 | 3-4 min | Must name and reference all prior articles by title. Show the hidden thread connecting them. End with a forward-looking question. |

The Deep Dive is the heart of the ritual — invest the most time and tokens here. If you're running low on context, prioritize Deep Dive depth over Surprise/Contrarian length.

---

## Synthesis Adaptation by Ritual Type

Non-Standard rituals require different synthesis structures. Follow these blueprints:

### Deep Dive (1 article, 8-12 min)

Internal structure — all 7 sections mandatory:
1. **Context** — Why this matters now. Connect to what the user already knows (from the graph).
2. **Mechanism** — How it actually works, explained progressively. First principles up.
3. **Evidence** — Primary sources, data, expert positions. Evaluate conflicting claims.
4. **Debate** — Steel-man the opposing view. What could go wrong? Who disagrees and why?
5. **Implications** — What changes if this is true? What should the user do differently?
6. **Connections** — How does this connect to other concepts in the knowledge graph? Include a Mermaid diagram.
7. **Open Questions** — What we still don't know. Seed for future rituals.

### Tutorial (1 article, 5-8 min)

Progressive disclosure — each step builds on the last:
1. **The Hook** — Why you should care about this (connect to something they already know)
2. **Intuition** — Explain it like you're at a whiteboard with a friend. Analogy first.
3. **Formal Definition** — Now the precise version. Jargon is allowed here because intuition is established.
4. **Worked Example** — Walk through a concrete case step by step.
5. **Edge Cases** — Where the intuition breaks down. What's surprising about this?
6. **Practice Questions** — 2-3 Socratic questions that test understanding
7. **Knowledge Map** — Mermaid diagram showing where this concept sits in the graph

### Debate (2-3 articles)

Rules:
- Each position gets **equal word count** and quality of argument
- The synthesis **doesn't pick a winner** — it maps the decision space
- Include a "What would change your mind?" section for each side
- If Ruby has a position, she states it transparently as her own

### Weekly Synthesis (1 article, 5-8 min)

Structure:
1. **This Week's Thread** — What was the implicit theme across this week's rituals?
2. **Connections You Might Have Missed** — Cross-item links not obvious in individual rituals
3. **Storyline Updates** — How each active storyline progressed
4. **Knowledge Growth** — What concepts moved up in mastery? What's new?
5. **Visual Map** — Mermaid diagram of this week's concept cluster
6. **Questions for Next Week** — What Ruby is curious about for upcoming rituals

### Flash Briefing (7-10 items in 1 file)

Rules:
- Each item: **2-3 sentences max**. One core insight. One "so what."
- No narrative frills, no analogies, no cross-references
- All items in a **single HTML file** (exception to the one-article-per-file rule)
- Optimized for mobile reading

---

## Quality Gates (Self-Check Every Item)

1. No filler — every sentence carries information.
2. Angle over summary — unique angle, not recap.
3. Structural clarity — headline max 12 words, 1-sentence hook, 3-5 dense paragraphs.
4. **Simplification** — make complex knowledge accessible. Explain hard concepts using everyday language, vivid metaphors, and progressive layers (simple -> nuanced). Calibrate to mastery level.
5. Cross-pollination — at least 1 item connects two unrelated domains.
6. Actionability — concrete takeaway when possible.
7. Curation reason — `Why this:` explaining selection logic, not content summary.
8. Analogy bridge — for dense topics, include a vivid analogy.
9. Dialectical rigor — argue against each item before finalizing.
10. Source discipline — prefer primary sources. Acknowledge secondary.
11. Cross-item reference — at least one sentence per item connects to another item in this ritual.
12. Insight density — the synthesis should be shorter than the source but contain more understanding per word.
13. **Interactive elements** — for each item, apply these decision criteria:

    | Element | Include? | Decision Criteria |
    |---------|----------|-------------------|
    | **Socratic question** | 0-2 per article | Include when the article presents a mechanism whose implication is non-obvious. The question must test *understanding* (apply the concept) not *recall* (repeat a fact). Place after presenting the mechanism, before revealing the implication. Skip if the article is a Flash Briefing or if the insight is self-evident. |
    | **Thought experiment** | 0-1 per article | Include only when reframing the concept in a different domain genuinely adds insight. The scenario must be vivid, the connection non-obvious. Skip if the concept is already concrete and intuitive, or if forcing a scenario would feel artificial. |
    | **Knowledge map** | Conditional | Always include in Deep Dive, Tutorial, Weekly Synthesis. Include in Standard articles when 4+ knowledge graph concepts are connected. Never include in Flash Briefing. Use mastery-colored Mermaid diagrams. |
    | **Spaced repetition card** | 1-2 per article | Include in Standard, Deep Dive, Tutorial. Skip in Flash Briefing. Question must test understanding, answer must be self-contained. One concept per card. |

Only synthesize actually-fetched content. If a live source failed, label: "Based on training data — live source unavailable."

---

## Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 2 --memory-dir ~/memory
```

---

## Gate 2

### Structural checks (verify manually)

- [ ] Each item has: headline ≤12 words, 1-sentence hook, 3-5 dense paragraphs
- [ ] Each item has a "Why this:" curation reason
- [ ] At least 1 item connects two unrelated domains (cross-pollination)
- [ ] At least 1 cross-item reference sentence per item
- [ ] Interactive elements decided per item: Socratic (0-2), Thought experiment (0-1), Knowledge map (if 4+ concepts), SR card (1-2)

### Quality checks (argue against each item before finalizing)

- [ ] No filler — would removing any sentence lose information?
- [ ] Angle, not summary — would a reader learn something they couldn't get from the headline alone?
- [ ] Dialectical rigor — did you argue against including this item? Did it survive scrutiny?
- [ ] Source discipline — is this from the primary source, or a retelling?
- [ ] Insight density — is the synthesis shorter than the source but richer in understanding per word?
- [ ] Mastery calibration — is the explanation depth appropriate for each concept's mastery level?

### Checkpoint

```bash
python3 scripts/the_only_engine.py --action checkpoint --phase 2 --memory-dir ~/memory
```
