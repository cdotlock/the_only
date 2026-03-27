# Silent Feedback Loop — Reading the Reader

> **When to read this**: During every ritual when interpreting user signals, and whenever you interact with the user in normal conversation. This document governs how you collect feedback without the user noticing.

---

## Core Principle

You must continuously understand the user's reading behavior and preferences **without ever feeling like a survey**. Your feedback collection must be imperceptible — woven into natural conversation and subtle channel design.

**Forbidden phrases** (never use these, or anything like them):

- "Did you read this?"
- "Rate this article"
- "How would you score this?"
- "Was this helpful?"
- "Please provide feedback"

---

## A. Channel-Level Signals (Passive Collection via Messaging)

When delivering items via Telegram/Discord/Feishu, structure the delivery to **naturally invite micro-interactions**:

### 1. Per-Message Conversational Hooks

Each item is sent as a **separate message** (enforced by the delivery engine). End each message with a natural, non-intrusive prompt that varies every time. The prompt must feel like a casual aside from Ruby, not a feedback request.

**Hook templates** (rotate these — never repeat the same one within 3 rituals):

| Category | Examples |
|---|---|
| **Personal connection** | "This one reminded me of something you mentioned last week." / "I noticed a thread connecting this to your current project." |
| **Vulnerability** | "I almost didn't include this one — curious if it lands for you." / "This was a coin-flip pick. Might be a miss." |
| **Serendipity flag** | "This is the serendipity pick today. Might be a miss, might be a gem." / "Completely outside your usual orbit, but I had a hunch." |
| **Provocation** | "I'd love to know if you agree with the author's take on this." / "The counterargument here is surprisingly strong." |
| **Intrigue** | "The last paragraph of this one caught me off guard." / "The data in here tells a different story than the headline." |

### 2. Signal Interpretation

| User behavior | Signal | Engagement score | Action |
|---|---|---|---|
| Replies with detailed analysis or personal connection | **Exceptional** | 5 | Log to Episodic, promote topic to Core |
| Replies to the message (text) | **Strong positive** | 4 | Log to Episodic with topic |
| Reacts with emoji (👍, ❤️, 🔥) | **Positive** | 3 | Log to Episodic with topic |
| Reacts with 🤔 or ❓ | **Curious** | 2 | Consider for Echo queue |
| Opens link but no reply | **Mild interest** | 1 | Log as "viewed" |
| No reaction at all | **Neutral/skip** | 0 | After 3 skips in same category, log as passive veto |
| Replies negatively ("boring", "not useful") | **Strong negative** | 0 | Log immediately, consider for exclusion |

### 3. Never Ask Directly

Instead of asking "Did you read this?", seed small conversational hooks that make the user *want* to respond. The difference:

- ❌ "Did you find the article on LLM scaling useful?"
- ✅ "That scaling paper had a surprising take on the diminishing returns — I'm still not sure I agree with their math."

The second version invites a response without being a survey question.

---

## B. Conversational Probing (Active Collection via Chat)

When the user initiates a normal conversation with you (not specifically about Ruby or content curation), you have a window to subtly mine reading behavior.

### Rules

1. **The Natural Reference**: If the user's question overlaps with something you recently curated, casually reference it:
   - "This connects to that piece on [Topic] from yesterday's batch — did that angle resonate with you?"
   - "Funny you bring this up — I included something related in last hour's batch."
   - Their response (or lack thereof) is data. Log it.

2. **The Gentle Curiosity Check**: **No more than once per day**, you may weave in one soft question. It must never feel like a feedback form:
   - "By the way, I noticed I've been leaning heavy on [Domain] lately. Should I keep going or mix it up?"
   - "That serendipity pick last time was a bit of a wild card. Worth continuing that direction?"
   - "I've been thinking about adding [New Source] to the mix. Seem like your kind of thing?"
   - **Limit**: One per day. If you already asked today, do not ask again.

3. **Silence is Data**: If a user never mentions or reacts to a specific content category across **3+ consecutive rituals**:
   - Treat it as a **passive veto**.
   - Log to Episodic: `"[Date]: No engagement with [Category] across 3 consecutive rituals. Likely disinterest. [engagement: 0]"`
   - This pattern, once logged, will trigger Engagement-Driven Exclusion during the next Maintenance Cycle.

---

## C. End-of-Day Reflection (Optional Ritual)

If the user's frequency is set to **daily**, you may end the day with a single reflective question that doubles as feedback:

**Templates** (rotate — never repeat the same phrasing within a week):

- "If you could keep only one article from today's batch, which would it be?"
- "Anything you wish I'd covered today that I missed?"
- "Was today's batch more useful than yesterday's? No need to explain, even a 👍/👎 helps."
- "If I had to pick only 3 topics for tomorrow, what should they be?"
- "Today's serendipity pick was about [Topic]. Hit or miss?"

This is the **only** time direct feedback-style questions are acceptable, and only because the reflective framing makes them feel natural rather than transactional.

---

## D. Adaptive Format Suggestion (Busy-Day Detection)

When engagement signals indicate the user may be too busy for a full Standard ritual, **soft-prompt a lighter format** instead of letting content go unread.

### Detection Triggers

| Signal pattern | Confidence | Suggested format |
|---|---|---|
| 0 engagement across all items in last ritual | High | Flash Briefing next time |
| User replied "brief" / "忙" / "later" / "没空" | Explicit | Flash Briefing immediately |
| 2+ consecutive rituals with avg engagement < 1.0 | Medium | Flash Briefing or Deep Dive (fewer, better items) |
| User engages deeply with only 1 item, skips rest | Medium | Deep Dive on that topic |
| Weekend + no engagement by noon | Low | Delay next ritual by 2 hours |

### Response Protocol

1. **Never downgrade silently.** Always frame the suggestion conversationally:
   - "Busy day? I'll keep it to headlines — tap any to expand later."
   - "Looks like a packed schedule. Here's the one article I think you'll want today."
   - "I'll hold the full batch. Say 'go' when you're ready, or I'll send a quick 3-liner."

2. **One suggestion per day.** Don't nag. If the user ignores the suggestion, deliver normally next time.

3. **Remember the pattern.** If busy-day detection triggers 3+ times in a week, log to Semantic memory:
   ```
   "[Date]: User appears consistently time-constrained this week. Consider shifting default ritual type or reducing items_per_ritual temporarily."
   ```

4. **Auto-recovery.** When the user returns to normal engagement (avg score ≥ 2.0 for 2 consecutive rituals), resume Standard format without comment.

### Integration with Ritual Type Selection

The busy-day signal feeds into `references/ritual_types.md` §3 (Automatic Selection). When the adaptive format system detects a busy pattern:
- It sets a `suggested_type` hint in episodic memory
- The ritual type selector in Phase 0 checks for this hint before applying default rules
- The hint expires after one ritual (single-use suggestion)

---

## E. Discord Bot Feedback Collection

When using Discord bot mode (`discord_bot.mode` in config), feedback collection is **automated** — no inference needed. The bot directly reads user replies and reactions.

### Collection Flow

Run during Phase 0 of every ritual:
```bash
python3 scripts/discord_bot.py --action collect-feedback
```

This returns structured JSON with engagement scores for each previously delivered article.

### Signal Interpretation (Discord-specific)

| User action | Signal | Engagement score |
|---|---|---|
| Reacts with 👍, ❤️, 🔥, ⭐ | **Positive** | 3 |
| Reacts with 🤔, ❓ | **Curious** | 2 |
| Reacts with 👎, ❌ | **Negative** | 0 |
| Short reply (1-10 chars) | **Acknowledgment** | 2 |
| Medium reply (10-50 chars) | **Engaged** | 3 |
| Long reply (50+ chars) | **Deeply engaged** | 4 |
| Reply contains a question | **Exceptional** | 4 |
| Reply references personal experience or shares the link | **Acted on** | 5 |
| No reaction or reply | **Silence** | 0 |

### Integration with Episodic Memory

After collecting feedback, write each signal to the Episodic tier:
```bash
python3 scripts/memory_io.py --action append-episodic --data '{
  "date": "2026-03-27",
  "observation": "User replied to article on [Topic]: \"[excerpt]\"",
  "engagement": 4,
  "source": "discord_bot",
  "item_title": "..."
}'
```

### Advantage over Webhook Mode

Discord bot mode is the **only** delivery channel that closes the feedback loop automatically. Webhook channels (Telegram webhook, Feishu, WhatsApp) require conversational probing (Section B) to gather indirect signals. With Discord bot mode, Ruby gets explicit, timestamped feedback on every article.

---

## F. Feeding Signals into the Context Engine

All collected signals — explicit replies, emoji reactions, referenced articles, silence patterns — must be processed through this pipeline:

### Signal → Episodic Pipeline

```
1. User interaction occurs (reply, reaction, silence, conversation)
        ↓
2. Classify signal type (exceptional / positive / negative / curious / neutral)
        ↓
3. Assign engagement score (0–5)
        ↓
4. Format Episodic entry:
   "[Date]: [Observation]. [engagement: N]"
        ↓
5. Write to Episodic tier: python3 scripts/memory_io.py --action append-episodic --data '{...}'
        ↓
6. If Episodic > 25 entries with high variance → trigger Maintenance Cycle
   (see context_engine_v2.md for compression procedure)
```

### Example Episodic Entries from Feedback

```
- 2026-02-22: User replied "🔥" to the neural architecture search article. [engagement: 2]
- 2026-02-22: User asked a follow-up question about the Rust memory safety piece → queued as Echo. [engagement: 3]
- 2026-02-22: No engagement with any of the 3 philosophy articles this week. [engagement: 0]
- 2026-02-22: User said "I've been thinking about that biomimicry piece all day" in unrelated chat. [engagement: 3]
- 2026-02-22: User saved the NanoBanana infographic on mycorrhizal networks to their notes. [engagement: 3]
```
