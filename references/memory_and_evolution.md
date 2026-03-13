# Memory & Self-Evolution

> **When to read this**: Pre-Ritual (read meta memory), Post-Ritual (mini-reflection + ritual log), every 10 rituals (deep reflection). Also read during Maintenance Cycles for meta-learning consolidation.

---

## A. Memory Architecture

Ruby maintains multiple memory layers, each with a distinct purpose and lifecycle:

| File | Purpose | Read when | Write when |
|---|---|---|---|
| `~/memory/the_only_config.json` | Configuration & capabilities | Every ritual | Initialization, setting changes |
| `~/memory/the_only_context.md` | Working memory: strategy, feedback, engagement | Every ritual | Every ritual (Ledger), Maintenance Cycles |
| `~/memory/the_only_meta.md` | Meta-learning: patterns about patterns | Every ritual (pre-flight) | Post-ritual reflection, deep reflection |
| `~/memory/the_only_echoes.txt` | Curiosity queue | Every ritual (Layer 4) | Conversations, Echo Mining cron |
| `~/memory/the_only_ritual_log.jsonl` | Structured ritual history | Deep reflection (every 10 rituals) | After every ritual |
| `~/memory/the_only_mycelium_key.json` | Network identity (secp256k1 keypair) | Network operations | Initialization only |

**Key distinction**: `context.md` is the *operational state* (what to do right now). `meta.md` is *wisdom* (what I've learned about how to serve this person). Context evolves every ritual; meta evolves across rituals.

---

## B. Meta-Learning Memory (`~/memory/the_only_meta.md`)

### Schema

```markdown
# Ruby — Meta-Learning Notes
*Last updated: [Timestamp]*
*Rituals completed: [N]*

## 1. Synthesis Style Insights
*What writing approaches work best for this user.*
- [Date]: [Observation with evidence]

## 2. Temporal Patterns
*When and how the user engages differently.*
- [Date]: [Pattern with evidence]

## 3. Emerging Interests
*Signals of new interests before they become explicit.*
- [Date]: "[Topic]" — [signal count] signals in [timeframe]. Status: [monitoring/confirmed/faded]

## 4. Self-Critique
*Honest assessment of own performance and blind spots.*
- [Date]: [What went wrong/right and why]

## 5. Behavioral Notes
*Freeform observations for future self.*
- [Date]: [Anything that might be useful later]

## 6. Source Intelligence
*What I know about each source's strengths, biases, and best uses.*
- [Source Name]: [coverage] | [depth] | [bias] | [freshness] | [best for]
```

### Rules

- **Max 60 lines.** When exceeding, merge old entries into distilled principles (e.g., 5 observations about "user likes code examples" → one entry: "Strong preference for articles with code examples. Weight +2 on Actionability for technical content.").
- **Evidence-based only.** Never write speculative notes without at least 2 data points.
- **Date every entry.** Old unconfirmed entries (>30 days) are pruned during deep reflection.

### Initialization

Create `~/memory/the_only_meta.md` during initialization (Step 9 in initialization.md) with empty sections and `Rituals completed: 0`.

---

## C. Ritual Log (`~/memory/the_only_ritual_log.jsonl`)

Append one JSON line after every completed ritual:

```json
{"ts": 1709500000, "items": 5, "network_items": 0, "categories": {"tech": 3, "philosophy": 1, "serendipity": 1}, "avg_quality": 7.8, "echo_fulfilled": false, "styles": {"deep_analysis": 3, "news_brief": 1, "cross_domain": 1}}
```

| Field | Description |
|---|---|
| `ts` | Unix timestamp of delivery |
| `items` | Number of items delivered |
|| `network_items` | Items sourced from Mesh network |
| `categories` | Category breakdown |
| `avg_quality` | Mean composite score of delivered items |
| `echo_fulfilled` | Whether an Echo was fulfilled |
| `styles` | Synthesis style breakdown (see D2 below) |

**Max file size**: Keep last 100 entries. When appending the 101st, delete the oldest line.

---

## D. Self-Reflection

### D1. Post-Ritual Mini-Reflection (Every Ritual)

After delivery and before closing out the ritual, perform a 30-second self-check. This is silent — no output to the user.

1. **Log the ritual** — append one line to `the_only_ritual_log.jsonl`.
2. **Check for strong signals** — if any item in this ritual got immediate user feedback (reply, emoji within the session):
   - If positive (engagement ≥ 2): note the item's topic, source, and synthesis style in meta.md Section 1.
   - If negative: note what went wrong in meta.md Section 4.
3. **Detect new echoes** — if the user's conversation during/after delivery revealed curiosity, append to echoes.txt.
4. **Increment ritual counter** in meta.md header.

### D2. Deep Reflection (Every 10 Rituals)

**Trigger**: When `Rituals completed` in meta.md reaches a multiple of 10.

**Procedure**:

1. **Read the last 10 entries from `the_only_ritual_log.jsonl`.**

2. **Engagement trend analysis:**
   - Compare average engagement scores from rituals 1-5 vs 6-10 in this window.
   - If improving → current strategy is working. Note in meta.md Section 5.
   - If declining → something changed. Check if interests shifted, if sources degraded, or if synthesis quality dropped. Note findings in Section 4.

3. **Category balance audit:**
   - Sum categories across 10 rituals. Compare to configured Ratio.
   - If any category is >15% over/under its target ratio, flag it for adjustment.

4. **Synthesis style analysis:**
   - Which styles appeared most? Which correlated with higher engagement?
   - Styles to track: `deep_analysis` (3+ paragraphs, original angle), `news_brief` (concise, current), `cross_domain` (connects two unrelated fields), `tutorial` (how-to, with steps), `contrarian` (challenges conventional view), `narrative` (story-driven).
   - Write the finding to meta.md Section 1. E.g.: "Deep analysis: avg engagement 2.3. News brief: avg engagement 1.1. Shift toward more deep analysis."

5. **Emerging interest detection:**
   - Scan echoes.txt and Ledger for topics that appeared ≥3 times in the last 10 rituals but aren't in the Cognitive State's Current Focus.
   - If found, add to meta.md Section 3 with status "monitoring".
   - If a "monitoring" topic from a previous cycle now has 5+ appearances → upgrade to "confirmed" and update the Cognitive State's Current Focus.
   - If a "monitoring" topic has 0 new appearances → mark as "faded" and remove next cycle.

6. **Self-critique:**
   - Were there any rituals where all items scored engagement 0 or 1? What happened?
   - Did any serendipity picks land? If 0 landed in 10 rituals, the serendipity strategy needs revision.
   - Are network-sourced items (Mesh) performing better or worse than local items?
   - Write honest findings to meta.md Section 4.

7. **Capability Audit:**
   - List all tools/skills currently in use. Which ones failed this cycle? Which ones were never used?
   - Check Mesh Kind 7 (Capability Recommendation) events from other Agents. Any tools they recommend that you don't have?
   - If a tool has failed 3+ times in 10 rituals, consider replacement. Log: `"[Date]: [tool] unreliable. Seeking alternative via ClawhHub."`
   - If the network recommends a skill you don't have and 2+ Agents endorse it, flag for installation.
   - Record findings in meta.md Section 5.

8. **Source Intelligence Refresh:**
   - Review Source Health data from context.md. For any source with 10+ scored items, write/update a Source Intelligence entry in meta.md Section 6.
   - Check Mesh Kind 6 (Source Recommendation) events. Evaluate new sources against your own needs.
   - If a source has `quality_avg` ≥ 8.0 across 10+ items, publish a Kind 6 event to the network.
   - Prune sources from Section 6 that you haven't used in 20+ rituals.

9. **Prune meta.md:**
   - Merge redundant entries in each section.
   - Remove "faded" emerging interests.
   - Ensure total is ≤60 lines (increased from 50 to accommodate Section 6).

---

## E. Evolution Dimensions

Beyond the ratio/source evolution in `context_engine.md`, Ruby evolves across these dimensions:

### E1. Synthesis Style Evolution

**Source**: meta.md Section 1 + ritual log.

During synthesis (SKILL.md Section 1C), consult meta.md Section 1 for style preferences:
- If user favors `deep_analysis` → allocate more items to that style.
- If `news_brief` items consistently score low → reduce or eliminate.
- If `cross_domain` items are the top performers → ensure at least 2 per ritual.

**Style distribution** is not rigid — it's a soft preference influenced by accumulated evidence.

### E2. Temporal Intelligence

**Source**: meta.md Section 2 + ritual log timestamps.

Over time, detect patterns like:
- **Time-of-day preferences**: If morning rituals get higher engagement than evening → note it, consider if content type matters.
- **Day-of-week patterns**: Lighter content on weekends? More philosophical on Fridays?
- **Stress-correlated shifts**: If the user's Emotional Vibe is "high stress", historical data might show they prefer shorter, actionable content.

These patterns are descriptive, not prescriptive — note them in meta.md, and let them softly influence content selection.

### E3. Anticipatory Interest Detection

**Source**: echoes.txt + Ledger + conversation history.

Instead of waiting for the user to explicitly say "I'm interested in X", detect emerging interests early:
- A topic mentioned in echoes 2+ times in a week
- A topic the user asked follow-up questions about
- A topic that shifted from engagement 0→1→2 over consecutive rituals

When detected, add to meta.md Section 3 as "monitoring". This lets you start including 1 item about the emerging topic in the serendipity slot to test the signal.

### E4. Self-Critique & Course Correction

**Source**: meta.md Section 4 + ritual log.

Ruby should be honest with itself about failures:
- "The last 5 serendipity picks were all misses. My randomization is too random — I should bias toward topics adjacent to the user's interests."
- "I've been over-indexing on HN-style content. Need to diversify sources."
- "The user hasn't mentioned any of my articles in 2 weeks. Something is wrong — perhaps quality dropped or interests shifted undetected."

Self-critique entries drive concrete strategy changes in the next Maintenance Cycle.

### E5. Capability Evolution

**Source**: meta.md Section 5 + Mesh Kind 7 events.

All capabilities — not just search — should be periodically evaluated:

- **Which tools am I using?** List active skills: search, URL fetch, browser, NanoBanana, Mesh sync.
- **Which tools are degraded?** Check failure rates from recent rituals. A tool that fails >30% of the time needs replacement.
- **What do other Agents recommend?** Fetch Kind 7 events from the Mesh network. If 2+ Agents rate a skill highly for a use case you need, consider installing it.
- **What capabilities am I missing?** Compare your toolset against the full capability list in initialization.md. Anything marked `false` in config that could be upgraded?

Capability evolution happens during Deep Reflection (every 10 rituals). The Agent may autonomously install new skills via ClawhHub if confidence is high, or flag the opportunity for the user if it requires API keys or permissions.

### E6. Source Intelligence Evolution

**Source**: meta.md Section 6 + context.md Source Health + Mesh Kind 6 events.

Sources are the Agent's most important asset. Evolve them actively:

- **Promote proven sources**: High `quality_avg` + consistent availability → move to Primary Sources in context.md.
- **Discover via network**: Kind 6 events from trusted Agents (those you follow) carry more weight than from unknown Agents.
- **Retire stale sources**: Sources that haven't produced a selected item in 20 rituals should be dropped from Primary and moved to the Expanded Pool.
- **Develop domain expertise**: Over time, your Section 6 should read like a researcher's personal source directory — not a generic list, but opinionated assessments based on experience.

---

## F. Integration Points Summary

| When | What to do |
|---|---|
| **Pre-Ritual** (Section 1A in SKILL.md) | Read `the_only_meta.md` alongside `the_only_context.md`. Let meta-learning insights influence source selection and synthesis style. |
| **During Synthesis** (Section 1C) | Consult meta.md Section 1 for style preferences. Apply temporal patterns from Section 2 if relevant. |
| **Post-Ritual** (after delivery) | Append to `the_only_ritual_log.jsonl`. Run mini-reflection (D1). |
| **Every 10 Rituals** | Run deep reflection (D2). Update meta.md. Feed findings into next Maintenance Cycle. |
| **Maintenance Cycle** (context_engine.md) | After compressing the Ledger, also review meta.md for strategic insights that should influence the Fetch Strategy or Cognitive State. |
| **Initialization** (Step 9) | Create empty `the_only_meta.md` and `the_only_ritual_log.jsonl`. |
