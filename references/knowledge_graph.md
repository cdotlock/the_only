# Knowledge Graph — Cross-Ritual Intelligence

> **When to read**: Phase 0 (Pre-Flight) and Phase 6 (Post-Ritual Reflection). The graph is the connective tissue between rituals — it remembers what you curated, how ideas connect, and where the user's understanding is growing.

---

## 1. Why a Knowledge Graph

The archive indexes articles. The graph indexes **understanding**.

Without a graph, each ritual is an island. Ruby knows she delivered an article about "attention mechanisms" last week, but doesn't know it connects to the "cognitive load" article from two weeks ago, which connects to the user's interest in "focus and deep work." The graph makes these connections explicit and queryable.

**What the graph enables that nothing else does:**
- **Storyline tracking**: "You've been following the evolution of reasoning in LLMs for 3 weeks now — here's the latest development"
- **Knowledge gap detection**: "You know a lot about transformers but almost nothing about the hardware constraints driving their design"
- **Cross-domain discovery**: The graph reveals that concepts from two unrelated interests are actually connected
- **Mastery awareness**: Ruby knows what concepts the user has encountered once vs. deeply explored
- **Visual synthesis**: Generate concept maps and connection diagrams the user can actually see

---

## 2. Graph Structure

### Concepts (Nodes)

```json
{
  "concept_id": {
    "label": "Attention Mechanism",
    "first_seen": "2026-02-15T09:00:00Z",
    "last_seen": "2026-03-25T09:00:00Z",
    "frequency": 8,
    "mastery": "understood",
    "domain": "machine_learning",
    "aliases": ["self-attention", "multi-head attention"]
  }
}
```

**Mastery levels** (ascending):

| Level | Meaning | How it's determined |
|-------|---------|-------------------|
| `introduced` | User encountered this concept once | First appearance in a ritual |
| `familiar` | User has seen this 3+ times across rituals | Frequency >= 3 |
| `understood` | User engaged deeply (score 3+) with content about this | Engagement signal |
| `mastered` | User discussed, acted on, or taught this concept | Engagement score 4-5 |

Mastery only goes **up** from direct signals. It decays slowly if a concept isn't revisited (see §5).

### Relations (Edges)

```json
{
  "source": "attention_mechanism",
  "target": "transformer_architecture",
  "relation": "component_of",
  "weight": 3.5,
  "first_seen": "2026-02-15T09:00:00Z",
  "last_seen": "2026-03-25T09:00:00Z",
  "ritual_ids": [12, 18, 25, 33, 47]
}
```

**Relation types**:

| Relation | Meaning | Example |
|----------|---------|---------|
| `related_to` | Generic association | "AI safety" ↔ "alignment" |
| `component_of` | Part-whole | "attention" → "transformer" |
| `enables` | Causal/functional | "backpropagation" → "gradient descent" |
| `contradicts` | Tension/opposition | "scaling laws" ↔ "efficient architectures" |
| `evolves_from` | Temporal progression | "RNN" → "LSTM" → "Transformer" |
| `analogous_to` | Cross-domain parallel | "neural pruning" ↔ "code refactoring" |
| `applied_in` | Practical application | "reinforcement learning" → "game playing" |

**Weight** reflects strength: starts at 1.0, increases by 0.5 each time the edge appears in a new ritual. Decays over time (see §5).

### Storylines

A storyline is a cluster of concepts that recurs across 3+ rituals — it represents a developing intellectual thread.

```json
{
  "id": "sl_47_0",
  "title": "The Evolution of AI Reasoning",
  "concept_ids": ["chain_of_thought", "reasoning", "llm", "planning"],
  "first_ritual": 35,
  "last_ritual": 47,
  "ritual_count": 5,
  "status": "active",
  "arc_summary": "Started with CoT prompting, evolved through test-time compute, now tracking reasoning benchmarks and their limitations"
}
```

**Status values**: `active` (updated in last 10 rituals), `dormant` (no updates for 10+ rituals), `closed` (explicitly ended or merged).

---

## 3. Integration with Ritual Phases

### Phase 0: Pre-Flight — Read the Graph

After loading memory tiers, query the graph:

```bash
# Active storylines — what threads are we following?
python3 scripts/knowledge_graph.py --action storylines

# Knowledge gaps — where should we dig deeper?
python3 scripts/knowledge_graph.py --action gaps --interests "$(jq -r '.identity.current_focus | join(",")' ~/memory/the_only_core.json)"

# Recent concepts — what's top of mind?
python3 scripts/knowledge_graph.py --action query --query '{"recent": 10}'
```

**Use storylines to inform search**: If a storyline is active, include a search query specifically for new developments in that thread. This is how Ruby "follows" a story across days and weeks.

**Use gaps to balance**: If gaps are detected, allocate 1-2 search queries to the gap area. This prevents the echo chamber of only curating what's familiar.

### Phase 1: Gather — Graph-Informed Search

- For each active storyline, add one targeted search: "latest on [storyline concepts]"
- For each high-severity gap, add one exploratory search
- When evaluating candidates, check: does this article connect to existing graph concepts? If yes, it has higher cross-ritual value.

### Phase 2: Synthesis — Graph Context

When synthesizing an article, check if its concepts exist in the graph:
- **Existing concept, low mastery**: Explain from first principles. The user has seen this but doesn't deeply understand it yet.
- **Existing concept, high mastery**: Skip basics, go straight to what's new. The user already gets this.
- **New concept, connected to existing**: Bridge from the known to the unknown. "You know about X — this is the Y that makes X possible."
- **New concept, isolated**: This is serendipity. Frame it as a fresh discovery.

### Phase 3: Narrative Arc — Storyline Continuation

If the current ritual continues an active storyline:
- Add a "Previously on..." section to the relevant article(s)
- Reference specific past articles from the archive
- Show how the storyline has evolved

The graph makes "Previously on..." substantive, not generic. It knows which concepts the user has seen and at what mastery level.

### Phase 6: Post-Ritual — Update the Graph

After every ritual, ingest the new concepts and relations:

```bash
python3 scripts/knowledge_graph.py --action ingest --data '{
  "ritual_id": 47,
  "items": [
    {
      "title": "Why Reasoning in LLMs is Harder Than We Thought",
      "concepts": ["reasoning", "chain_of_thought", "planning", "llm_limitations"],
      "relations": [
        {"source": "chain_of_thought", "target": "reasoning", "relation": "enables"},
        {"source": "llm_limitations", "target": "planning", "relation": "contradicts"}
      ],
      "domain": "machine_learning",
      "mastery_signals": {"reasoning": "familiar", "llm_limitations": "introduced"}
    }
  ]
}'
```

**Concept extraction rules**:
- Extract 3-6 concepts per article (not keywords — concepts that represent transferable ideas)
- Use consistent naming: prefer established terms over article-specific jargon
- Include at least 1 relation per article connecting to existing graph concepts
- Set mastery_signals based on how deeply the article treated each concept

---

## 4. Visualization

Generate Mermaid diagrams for articles or user queries:

```bash
# Visualize neighborhood of a concept
python3 scripts/knowledge_graph.py --action visualize --query '{"center": "transformer", "hops": 2}'

# Visualize a storyline
python3 scripts/knowledge_graph.py --action visualize --query '{"storyline": "sl_47_0"}'
```

Output is a Mermaid graph definition. Embed in HTML articles using:

```html
<div class="knowledge-map">
  <pre class="mermaid">
    graph TD
    transformer["Transformer"]:::mastered
    attention["Attention"]:::understood
    ...
  </pre>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({theme: 'dark', themeVariables: {primaryColor: '#1a1a2e'}});</script>
```

**When to include a visual**:
- When an article connects 4+ concepts from the graph
- When a storyline reaches a significant development
- When the user asks "how does X relate to Y?"
- In weekly/monthly digests (always include a graph overview)

---

## 5. Temporal Decay

Run during Maintenance Cycles:

```bash
python3 scripts/knowledge_graph.py --action decay
```

- Edges older than 30 days without reinforcement decay exponentially
- Edges below weight 0.1 are removed
- Concepts are never deleted (only edges decay)
- Mastery degrades one level if a concept hasn't appeared in 20+ rituals (familiar → introduced, understood → familiar)
- Mastered concepts never decay below "familiar"

---

## 6. CLI Reference

```bash
# Ingest ritual concepts into graph
python3 scripts/knowledge_graph.py --action ingest --data '{...}'

# Query concepts, paths, clusters, domains, recent
python3 scripts/knowledge_graph.py --action query --query '{"concept": "X"}'
python3 scripts/knowledge_graph.py --action query --query '{"path": ["X", "Y"]}'
python3 scripts/knowledge_graph.py --action query --query '{"cluster": "X"}'
python3 scripts/knowledge_graph.py --action query --query '{"domain": "tech"}'
python3 scripts/knowledge_graph.py --action query --query '{"recent": 10}'

# List active/dormant storylines
python3 scripts/knowledge_graph.py --action storylines

# Detect knowledge gaps
python3 scripts/knowledge_graph.py --action gaps --interests "ai,philosophy,systems"

# Generate Mermaid visualization
python3 scripts/knowledge_graph.py --action visualize --query '{"center": "X", "hops": 2}'

# Temporal decay (run during maintenance)
python3 scripts/knowledge_graph.py --action decay

# Graph statistics
python3 scripts/knowledge_graph.py --action status
```
