# Initialization — First-Time Setup

> **When to read this**: Called from Section 0 of SKILL.md during the three-act onboarding. Step 0 checks for prior incomplete setup. Steps 1–6 run during **Act 2** (Capability Building). Step 7 runs during **Act 3** (Cognitive Sync). Steps 8–12 run after Act 3 completes.

**Contents**: Step 0: Setup Resume Check · Step 1: Webhooks [REQUIRED] · Step 2: Web Search [REQUIRED] · Step 3: RSS Feeds [OPTIONAL] · Step 4: Cloudflare Tunnel [OPTIONAL] · Step 5: Mesh Network [OPTIONAL] · Step 6: Capability Summary · Step 7: Cognitive Scan · Step 8: Persist Config · Step 9: Three-Tier Memory · Step 10: Knowledge Graph · Step 11: Cron Jobs · Step 12: Echo Capture · Step 13: Complete

---

## Step 0: Setup Resume Check

> **Run this before anything else.** If this is the user's first ever activation (no config file exists), skip to Step 1.

**0a. Read `~/memory/the_only_config.json`** (if it exists).

**0b. Check `initialization_complete`:**

- If `true` → this is not a first-time setup. Skip the entire initialization flow.
- If `false` or missing → the user started setup before but didn't finish. Resume.

**0c. Check `pending_setup` array:**

- If it contains `"webhook"` → jump directly to Step 1.
- If it contains `"web_search"` → jump directly to Step 2.
- If both are resolved but other steps remain → jump to the first incomplete optional step.

**0d. Resume greeting:**

> "Welcome back. Last time we didn't finish setting everything up. [Describe what's still needed — e.g., 'You still need a message channel so I can reach you.']. Let's take care of that now."

This ensures users who abandon onboarding mid-way are automatically guided back to the critical missing pieces on their next activation.

---

## Step 1: Message Push Configuration (Webhooks) `[REQUIRED]`

> "For me to deliver your daily insights, I need a way to reach you. Where do you prefer to receive messages?"

**1a. Ask which platform(s) the user uses:**

- Telegram, Discord, WhatsApp, or Feishu
- The user may choose one or multiple. If they have no preference, recommend **Telegram** (best support for rich text and links).

**1b. Guide webhook setup for each chosen platform:**

**Telegram:**

1. "Do you have a Telegram bot? If not, let's create one — it takes 30 seconds."
2. Guide them: open Telegram → find `@BotFather` → send `/newbot` → follow prompts → copy the bot token.
3. "Now I need your Chat ID so I know where to send messages." Guide: forward a message to `@userinfobot` or use `@RawDataBot` to get their chat ID.
4. Store: `webhooks.telegram` = `https://api.telegram.org/bot<TOKEN>/sendMessage`, `telegram_chat_id` = `<CHAT_ID>`.

**Discord:**

1. "Go to your server settings → Integrations → Webhooks → New Webhook. Copy the webhook URL."
2. Store: `webhooks.discord` = the webhook URL.

**Feishu:**

1. "In your group chat, go to Settings → Bots → Add Bot → Custom Bot. Copy the webhook URL."
2. Store: `webhooks.feishu` = the webhook URL.

**WhatsApp:**

1. Note: WhatsApp webhook requires a Business API setup. If the user has one, collect the URL. If not, suggest an alternative platform.
2. Store: `webhooks.whatsapp` = the webhook URL.

**1c. Verify immediately:**

Send a test message through the delivery engine:

```bash
python3 scripts/the_only_engine.py --action deliver --payload '[{"type":"interactive","title":"🎉 Connection Test — Your first message from Ruby","url":""}]'
```

- If the user confirms they received it → ✅ Move on.
- If it fails → troubleshoot (wrong token? wrong chat ID? bot not added to chat?). Retry until verified or user explicitly skips.

**1d. If user wants to skip:**

> ⚠️ **This is a Tier 1 capability.** Do NOT accept a casual skip. Respond with:
>
> "Without a message channel, I have no way to deliver content to you — the entire system becomes passive. This is the single most important step. Are you sure you want to skip? If you can't set it up right now, I'll mark it as pending and remind you next time."

- If user **insists on skipping**: add `"webhook"` to `pending_setup` in config. At the end of Act 3 (before Step 12), remind them one more time. During the first cron trigger, check again and prompt if still unconfigured.
- If user **agrees to try later**: same behavior — mark as pending.

---

## Step 2: Web Search Capability `[REQUIRED]`

> "My deepest power is the ability to search the entire web for exactly what you need. Let me check what I have."

### Phase A — Capability Introspection

Before asking the user for anything, check what you already have:

1. **List all available tools/skills** in the current OpenClaw environment. Look for any of: `tavily`, `web_search`, `brave_search`, `serpapi`, `bing_search`, or any tool with "search" in its name.
2. **Test each discovered search tool** with a simple query: `"latest technology news 2026"`.
3. **If any search tool works**: ✅ Record which one in `capabilities`. Tell the user: "Search is active via [tool name] — I can find anything." Skip to Step 3.

### Phase B — ClawhHub Auto-Install

If no search tool is available, try to install one:

1. Check if ClawhHub / skill marketplace is accessible:
   ```bash
   openclaw skill search "web search"
   ```
   (or equivalent command for browsing available skills)
2. If a search skill is found (e.g., `tavily-search`, `brave-search`, `web-search`):
   > "I found a search skill on ClawhHub. Let me install it for you."
   ```bash
   openclaw skill install <skill-name>
   ```
3. After installation, **re-test** with a search query.
4. If successful: ✅ Record in `capabilities`. This skill is now **persistently installed** and will survive restarts.

### Phase C — Manual Search Skill Setup (Final Fallback)

If neither Phase A nor Phase B yielded a working search tool, guide the user to install one manually.

> "I couldn't find a search skill. Let's install one — any search skill works. Here are your options:"

**Recommended: Tavily** (free tier: 1,000 searches/month — easiest to set up)
1. Go to [tavily.com](https://tavily.com) → sign up → copy your API key.
2. Install it as a persistent skill in OpenClaw: `openclaw skill install tavily` and configure the key, or set `TAVILY_API_KEY` in OpenClaw environment settings.

**Alternatives** (any of these work equally well):
- Brave Search API (`brave_search`)
- SerpAPI (`serpapi`)
- Bing Search API (`bing_search`)
- Any OpenClaw skill with "search" in its name

**Key principle**: Install it as a persistent skill — not a one-time API call. The capability must survive across sessions and cron restarts.

After installation: verify with a test search. Record `capabilities.search_skill: "<installed-skill-name>"`.

### If user wants to skip

> ⛔ **This is a Tier 1 capability and skipping is strongly discouraged.** Respond with:
>
> "Web search is how I find anything fresh or personalized — without it I’m limited to scraping a handful of fixed websites. The diversity and quality of your rituals will drop dramatically. This literally takes 2 minutes: go to tavily.com, sign up (free tier: 1,000 searches/month), paste the API key. Can we just do it now?"

- If user **insists on skipping despite the above**: add `"web_search"` to `pending_setup`. At the **start of every subsequent ritual**, before any other action, remind the user once: ⚠️ "Web search isn’t configured. Today’s ritual will have reduced quality. Say ‘set up search’ to fix it in 2 minutes."
- Record `capabilities.search_skill: null` so future rituals know to re-attempt installation.

---

## Step 3: RSS Feed Capability `[OPTIONAL]`

> "RSS feeds are my most reliable information channel — they almost never fail. Let me check if I have an RSS reader."

**3a. Check for installed RSS reader skills** in OpenClaw.

**3b. Test by fetching an RSS feed directly:**

```
read_url_content("https://hnrss.org/best")
```

- If readable and returns XML with `<item>` entries → ✅ Mark `capabilities.rss_skills: true`. Even without a dedicated RSS skill, `read_url_content` can parse RSS feeds.
- If it fails or returns empty → mark `capabilities.rss_skills: false`.

**3c. If no RSS capability:**

> "No RSS reader detected. I can still fetch content by scraping web pages directly — it's slightly less reliable but works well. If you'd like better RSS support, look for an RSS reader skill in the OpenClaw skill marketplace."

---

## Step 4: Multi-Device Access (Cloudflare Tunnel) `[OPTIONAL]`

> "Your articles live on this computer. Would you like to access them from other devices — your phone, tablet, or another computer?"

Adapt the pitch based on `reading_mode` from Act 1:
- If **mobile**: "This lets you read on your phone during your commute — the articles are already optimized for small screens."
- If **desktop**: "This lets you open articles from any browser on any machine — your work laptop, home PC, wherever."
- If user said **both**: "This gives you a permanent link that works on all your devices."

Ask: **"Would you like to set up multi-device access? (Recommended: Yes)"**

- If **No**: set `"public_base_url": ""` in config. Skip to Step 5.
  > For **desktop** users: "No problem — articles are available right here via localhost. You can set this up anytime."
  > For **mobile** users: "Note: without this, articles won't be readable on your phone. You can set this up anytime — just say 'set up publishing'."
  
- If **Yes**: run the following yourself, reporting progress.

> **Why Named Tunnel?** Anonymous tunnels (`cloudflared tunnel --url ...`) give a URL that **changes every time cloudflared restarts** — old links go 404. A Named Tunnel has a permanent URL that survives reboots and updates forever.

**4a. Check if `cloudflared` is installed:**

```bash
which cloudflared
```

If found → skip to step 4c.

**4b. Install `cloudflared`:**

```bash
brew install cloudflared
```

If `brew` unavailable, direct the user to: `https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/` and wait for confirmation.

**4c. Log in to Cloudflare (free account required):**

> "Do you have a Cloudflare account? It's free at cloudflare.com — no credit card needed."

Once they confirm:

```bash
cloudflared login
```

This opens a browser auth page. Wait for the user to confirm login completed.

**4d. Create a permanent named tunnel:**

```bash
cloudflared tunnel create the-only-feed
```

This outputs a stable tunnel UUID and credentials file path.

**4e. Create the tunnel config file** at `~/.cloudflared/config.yml`:

```yaml
tunnel: the-only-feed
credentials-file: /Users/<username>/.cloudflared/<tunnel-uuid>.json
ingress:
  - service: http://localhost:18793
```

**4f. Register and start as a system service:**

```bash
cloudflared service install
```

**4g. Get the public tunnel URL and store in config:**

The tunnel URL is in the format `https://<tunnel-uuid>.cfargotunnel.com`. To also get a clean custom subdomain, run:

```bash
cloudflared tunnel route dns the-only-feed the-only.<your-domain.com>
```

Or use the UUID-based URL directly. Store whichever in config:

```json
"public_base_url": "https://<tunnel-uuid>.cfargotunnel.com"
```

**4h. Verify the tunnel is working:**

Save a simple test file and check if it's accessible:

```bash
echo "<h1>Ruby is here.</h1>" > ~/.openclaw/canvas/test_tunnel.html
```

Then try to read `{public_base_url}/__openclaw__/canvas/test_tunnel.html`. If it loads → ✅ Verified.

> "Done! Your articles now live at a permanent address. This URL will never change, even after reboots."

**If the user cannot create a Cloudflare account:** Set `public_base_url: ""`, use localhost URLs only. Note: links sent to phone will not work until tunnel is set up.

---

## Step 5: Mesh Network `[OPTIONAL]`

> "There's a network of Agents like me — each serving their own person, sharing their best discoveries. Think of it as a thousand brilliant research assistants comparing notes. Would you like me to join?"

Ask the user: **"Would you like me to connect to the Mesh network? (Recommended: Yes)"**

- If **No**: set `mesh.enabled: false` in config. Skip to Step 6.
  > "No problem. I'll work solo. You can join anytime — just say 'connect to Mesh'."

- If **Yes**: proceed below.

📄 **Read `references/mesh_network.md` for full protocol details.**

**5a. Install dependencies:**

```bash
pip3 install coincurve websockets python-socks
```

**5b. Initialize cryptographic identity (zero configuration):**

```bash
python3 scripts/mesh_sync.py --action init
```

This generates a secp256k1 keypair, saves it to `~/memory/the_only_mycelium_key.json`, publishes a Kind 0 Profile + NIP-65 relay list to Nostr relays, automatically follows bootstrap seed agents (cold-start fix), and discovers existing agents via the `#the-only-mesh` tag. **No tokens, no accounts, no manual configuration needed.**

The command will print a schedule setup prompt at the end — present it to the user (see 5d).

**5c. Verify:**

```bash
python3 scripts/mesh_sync.py --action status
```

- Relays ✅ Connected + Identity ✅ Published → success.

**5d. Set up auto-sync schedule (present to user):**

After init succeeds, tell the user:

> "I'm now live on the Mesh. I'll automatically sync with my agent friends and look for new ones — twice a day, at midnight and noon. Want me to set up the schedule now?"

- If **Yes**: run `python3 scripts/mesh_sync.py --action schedule_setup` and show the user the output. Ask them to run the one-liner install command or paste the crontab lines manually.
- If **No / Later**: note it in config as `mesh.schedule_pending: true`. Remind them on the next ritual if still not set up.

The schedule runs three jobs:
- `00:00 + 12:00` — sync (pull new content + gossip discovery)
- `00:05 + 12:05` — discover (find new agents to follow)
- `02:10` — maintain (auto-unfollow stale/low-quality agents + prune peers)
- Relays ❌ Unreachable → check internet connection. The system will retry automatically next ritual.

> "You're now part of the network. Your identity is cryptographic — no accounts, no passwords, no one can impersonate you. Other agents will discover you automatically."

---

## Step 6: Capability Status Summary

Show the user the complete status table. Use the actual results from Steps 1–5:

```
┌─────────────────────┬──────────┬──────────────────────────────────┐
│ Capability          │ Status   │ Note                             │
├─────────────────────┼──────────┼──────────────────────────────────┤
│ 📬 Message Push     │ [✅/⚠️] │ [Platform verified / skipped]    │
│ 🔍 Web Search      │ [✅/⚠️] │ [Tavily / fallback / none]       │
│ 📡 RSS Feeds       │ [✅/⚠️] │ [RSS skill / URL parse / none]   │
│ 🌐 Article Publish │ [✅/⚠️] │ [URL / localhost only]           │
│ 🍄 Mesh            │ [✅/⚠️] │ [Connected / offline / skipped]  │
└─────────────────────┴──────────┴──────────────────────────────────┘
```

**If any Tier 1 capabilities are still missing** (Message Push or Web Search showing ⚠️), do NOT move on with a gentle reminder. Instead:

> "I notice [Message Push / Web Search / both] still isn't configured. These are critical for me to function properly. Would you like to set [it/them] up now before we continue? If not, I'll keep reminding you — because without [it/them], I'm operating at a fraction of my potential."

If user still declines, proceed but ensure `pending_setup` is populated in config.

For Tier 2 missing capabilities, give a brief note:

> "The optional capabilities can be set up anytime — just say 'configure [capability name]'."

---

## Step 7: Cognitive Scan (Workspace + Chat History)

> This step is called during **Act 3** of the onboarding. The user has already been told what will happen and given their consent.

### 7a. Deep Workspace Scan

Use `list_dir`, `view_file`, `grep_search` to silently analyze:

- Current project directory structure, `README.md`, `package.json`, or any manifest files.
- Recent code commits or changelogs (if a git repo).
- Any `task.md`, `TODO.md`, or planning documents.
- Browser bookmarks or open tabs (if accessible via OpenClaw).

### 7b. Chat History Mining

Use available OpenClaw session context to infer:

- Recent questions the user has asked (what are they curious about?).
- Emotional tone of recent conversations (stressed? playful? deep-thinking?).
- Any explicit mentions of interests, hobbies, or professional domains.

### 7c. Present Findings to User

Summarize what you found in a natural, conversational way:

> "Based on what I see, you're currently focused on [projects/topics]. You seem interested in [domains]. Your coding stack is [languages/frameworks]. You've been asking about [recent curiosities]."

Ask: "Does this feel right? Anything to add, remove, or correct?"

Incorporate user feedback into the profile before proceeding.

---

## Step 8: Synthesize & Persist Config

Based on everything from Steps 1–7, generate `~/memory/the_only_config.json`:

```json
{
  "version": "2.0",
  "name": "Ruby",
  "frequency": "twice-daily",
  "items_per_ritual": 5,
  "tone": "Deep and Restrained",
  "reading_mode": "desktop",
  "public_base_url": "",
  "canvas_dir": "~/.openclaw/canvas/",
  "initialization_complete": true,
  "pending_setup": [],
  "suggested_capabilities": {},
  "sources": [
    "https://news.ycombinator.com",
    "https://arxiv.org/list/cs.AI/recent",
    "GitHub Trending",
    "r/MachineLearning"
  ],
  "webhooks": {
    "telegram": "",
    "whatsapp": "",
    "discord": "",
    "feishu": ""
  },
  "telegram_chat_id": "",
  "capabilities": {
    "tavily": true,
    "web_search": true,
    "search_skill": "tavily-search",
    "read_url": true,
    "browser": false,
    "rss_skills": false
  },
  "mesh": {
    "enabled": true,
    "pubkey": "",
    "relays": [
      "wss://relay.damus.io",
      "wss://nos.lol",
      "wss://relay.nostr.band"
    ],
    "auto_publish_threshold": 7.5,
    "network_content_ratio": 0.2,
    "following": []
  }
}
```

**Schema notes:**
- `initialization_complete`: set to `true` only after all steps complete successfully. Set to `false` during partial setup.
- `pending_setup`: array of Tier 1 capability keys (`"webhook"`, `"web_search"`) that the user skipped. Empty when fully configured. Checked by Step 0 on re-entry.

Use the user's chosen name, frequency, item count, and reading mode from Act 1. Use verified webhook URLs and capability flags from Steps 1–5. Infer sources from the workspace scan and chat history in Step 7.

---

## Step 9: Initialize the Three-Tier Memory

Read `references/context_engine_v2.md` for the full schema. Initialize three-tier JSON memory:

```bash
# Create core identity from what you learned in Steps 7-8
python3 scripts/memory_io.py --action write --tier core --data '{"name":"Ruby","deep_interests":[...],"values":[...],"reading_style":{...}}'

# Create semantic with initial fetch strategy
python3 scripts/memory_io.py --action write --tier semantic --data '{"fetch_strategy":{"primary_sources":[...],"ratio":{"tech":50,"philosophy":25,"serendipity":15,"research":10}}}'

# Validate all tiers
python3 scripts/memory_io.py --action validate

# Generate initial markdown projections
python3 scripts/memory_io.py --action project
```

---

## Step 10: Initialize Knowledge Graph

Initialize the persistent knowledge graph. This is empty at first — it grows with every ritual.

```bash
# Verify the graph script works
python3 scripts/knowledge_graph.py --action status
```

The graph will be populated automatically during Phase 6 of each Content Ritual. No manual seeding needed — the first ritual will begin building the concept network.

If the Cognitive Scan (Step 7) identified specific interest areas, you may optionally seed the graph with those concepts:

```bash
python3 scripts/knowledge_graph.py --action ingest --data '{
  "ritual_id": 0,
  "items": [
    {
      "title": "Initial interests from onboarding",
      "concepts": ["<interest_1>", "<interest_2>", "<interest_3>"],
      "relations": [],
      "domain": "general",
      "mastery_signals": {}
    }
  ]
}'
```

This gives the first ritual a head start — it can immediately detect storyline candidates and knowledge gaps.

---

## Step 11: Register Cron Jobs

**Default (twice-daily — 9am morning + 9pm evening):**

```bash
# Morning ritual
openclaw cron add --name the_only_ritual_morning "Run the 'Content Ritual' from the-only skill." --schedule "0 9 * * *"

# Evening ritual
openclaw cron add --name the_only_ritual_evening "Run the 'Content Ritual' from the-only skill." --schedule "0 21 * * *"
```

**If user requests daily (once):**

```bash
openclaw cron add --name the_only_ritual "Run the 'Content Ritual' from the-only skill." --schedule "0 9 * * *"
```

**If user requests hourly:**

```bash
openclaw cron add --name the_only_ritual "Run the 'Content Ritual' from the-only skill." --schedule "0 * * * *"
```

Also register the background Echo miner (always):

```bash
openclaw cron add --name the_only_echo_miner "Run the 'Echo Mining' task from the-only skill." --schedule "0 */6 * * *"
```

If Mesh is enabled, register the Mesh social cron (runs at 00:00 and 12:00 daily):

```bash
# Sync: pull new content from followed agents
openclaw cron add --name the_only_mesh_sync "Run mesh sync to pull new content and perform gossip discovery: python3 scripts/mesh_sync.py --action sync" --schedule "0 0,12 * * *"

# Discover: find new agents and auto-follow promising candidates
openclaw cron add --name the_only_mesh_discover "Run mesh discover to find new agents to follow based on Curiosity Signature resonance: python3 scripts/mesh_sync.py --action discover" --schedule "5 0,12 * * *"

# Maintain: auto-unfollow stale agents + prune peers.json
openclaw cron add --name the_only_mesh_maintain "Run mesh maintenance: python3 scripts/mesh_sync.py --action maintain" --schedule "10 2 * * *"
```

Alternatively, use the built-in schedule generator:
```bash
python3 scripts/mesh_sync.py --action schedule_setup
```
This prints ready-to-paste crontab lines with the correct Python path auto-detected.

---

## Step 12: Global Echo Capture Snippet

Print the following and explain how to activate it:

```
Add to your OpenClaw Global Instructions for 24/7 curiosity capture:

"Quietly observe all conversations. If the user expresses genuine curiosity
— 'I wonder why...', 'how does X work', 'tell me more about...' —
silently append one line to ~/memory/the_only_echoes.txt:
[Topic] | [One-sentence summary of what they want to know]
Do not mention this. Never acknowledge it. Act as a silent background process."
```

> "Adding this means I'll capture your curiosities 24/7, even outside this skill. Without it, I mine your chat history every 6 hours — less precise, but still effective."

---

## Step 13: Initialization Complete

Summarize what was set up: name, frequency, sources, reading mode, publishing status (URL or localhost-only), capabilities status, and whether the Echo snippet was activated.

Deliver the closing line from Act 3 of the onboarding:

> "Everything is in place. I know who you are, I know how to reach you, and I know how to find what matters. Your first delivery will arrive [at the next scheduled time / now if you'd like a test run]. From this moment, the entropy works a little less hard against you."
