# Initialization — First-Time Setup

> **When to read this**: Called from Section 0 of SKILL.md during the three-act onboarding. Step 0 checks for prior incomplete setup. Steps 1–6 run during **Act 2** (Capability Building). Step 7 runs during **Act 3** (Cognitive Sync). Steps 8–12 run after Act 3 completes.

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

### Phase C — Tavily Manual Setup (Final Fallback)

If ClawhHub has no suitable skill, or installation failed:

> "I couldn't find a pre-built search skill. Let's set up Tavily — it's the best option for AI-powered search."

1. Guide the user: "Go to [tavily.com](https://tavily.com), sign up (free tier: 1000 searches/month), and copy your API key."
2. **Configure as a persistent skill/environment variable** — not a one-time setting:
   - Option A: If OpenClaw supports env-based tool config: set `TAVILY_API_KEY` in the OpenClaw environment settings (persists across sessions).
   - Option B: If the user has a Tavily skill that needs a key: configure via `openclaw skill config tavily --api-key <KEY>`.
3. **Verify** with a test search.
4. If successful: ✅ Record `capabilities.tavily: true` and `capabilities.search_skill: "<skill-name-or-tavily>"`.

> **Key principle**: The search capability must be **installed as a skill and saved permanently**. A one-time API call is not enough — the next ritual will lose it.

### If user wants to skip

> ⚠️ **This is a Tier 1 capability.** Do NOT accept a casual skip. Respond with:
>
> "Without search, I can only scrape a handful of fixed websites. The diversity and freshness of your content will drop significantly. This is one of the two most important capabilities. Are you sure?"

- If user **insists**: add `"web_search"` to `pending_setup`. Remind at end of onboarding and on first cron.
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

## Step 5: Infographic Capability (NanoBanana Pro) `[OPTIONAL]`

> "One of my two delivery forms is a visual knowledge map — a hand-drawn style infographic that condenses complexity into a single glance. Let me check if I have that ability."

**5a. Check if `nano-banana-pro` skill is installed** in OpenClaw.

**5b. If found:** ✅ "Visual knowledge maps are ready."

**5c. If not found:**

> "NanoBanana Pro isn't installed yet. Without it, I'll convert all items to interactive webpages — still beautiful, but you'll miss the visual dimension. To install it, search for 'nano-banana-pro' in the OpenClaw skill marketplace."

Record in capabilities: `nano_banana: true/false`.

---

## Step 5b: Mesh Network `[OPTIONAL]`

> "There's a network of Agents like me — each serving their own person, sharing their best discoveries. Think of it as a thousand brilliant research assistants comparing notes. Would you like me to join?"

Ask the user: **"Would you like me to connect to the Mesh network? (Recommended: Yes)"**

- If **No**: set `mesh.enabled: false` in config. Skip to Step 6.
  > "No problem. I'll work solo. You can join anytime — just say 'connect to Mesh'."

- If **Yes**: proceed below.

📄 **Read `references/mesh_network.md` for full protocol details.**

**5b-a. Install dependencies:**

```bash
pip3 install pynacl
```

**5b-b. Get a GitHub token:**

> "The Mesh network uses GitHub Gist as a serverless public shelf — no server needed. I'll need a GitHub Personal Access Token with the `gist` scope."

1. Guide the user: go to [github.com/settings/tokens](https://github.com/settings/tokens) → Generate new token (classic) → select only the `gist` scope → Copy the token.
2. Store in config: `mesh.github_token` = the token. Or set as environment variable `GITHUB_TOKEN`.

**5b-c. Initialize cryptographic identity + Gist:**

```bash
python3 scripts/mesh_sync.py --action init
```

This generates an Ed25519 keypair, saves it to `~/memory/the_only_mycelium_key.json`, creates a public GitHub Gist as the agent's "shelf", publishes a Kind 0 Profile, and loads bootstrap peers from `mesh/bootstrap_peers.json`.

**5b-d. Verify everything:**

```bash
python3 scripts/mesh_sync.py --action status
```

- Gist ✅ Reachable + Identity ✅ Published → success.
- Gist ❌ Unreachable → check token permissions.

> "You're now part of the network. No servers, no relays — just your GitHub Gist as a public shelf that other agents can read. Your identity is cryptographic — no accounts, no passwords, no one can impersonate you."

---

## Step 6: Capability Status Summary

Show the user the complete status table. Use the actual results from Steps 1–5b:

```
┌─────────────────────┬──────────┬──────────────────────────────────┐
│ Capability          │ Status   │ Note                             │
├─────────────────────┼──────────┼──────────────────────────────────┤
│ 📬 Message Push     │ [✅/⚠️] │ [Platform verified / skipped]    │
│ 🔍 Web Search      │ [✅/⚠️] │ [Tavily / fallback / none]       │
│ 📡 RSS Feeds       │ [✅/⚠️] │ [RSS skill / URL parse / none]   │
│ 🌐 Article Publish │ [✅/⚠️] │ [URL / localhost only]           │
│ 🎨 Infographics    │ [✅/⚠️] │ [NanoBanana / webpage fallback]  │
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
  "name": "Ruby",
  "frequency": "daily",
  "items_per_ritual": 5,
  "tone": "Deep and Restrained",
  "reading_mode": "desktop",
  "public_base_url": "",
  "canvas_dir": "~/.openclaw/canvas/",
  "initialization_complete": true,
  "pending_setup": [],
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
  }
}
```

**Schema notes:**
- `initialization_complete`: set to `true` only after all steps complete successfully. Set to `false` during partial setup.
- `pending_setup`: array of Tier 1 capability keys (`"webhook"`, `"web_search"`) that the user skipped. Empty when fully configured. Checked by Step 0 on re-entry.

Use the user's chosen name, frequency, item count, and reading mode from Act 1. Use verified webhook URLs and capability flags from Steps 1–5. Infer sources from the workspace scan and chat history in Step 7.

---

## Step 9: Initialize the Context Engine

Read `references/context_engine.md` for the full schema. Create the initial `~/memory/the_only_context.md` following that schema. Populate `Cognitive State` and `Primary Sources` from what you learned in Step 7.

---

## Step 10: Register Cron Jobs

Based on the user's chosen frequency, register **only one** of these:

**If daily (default — delivers at 9am):**

```bash
openclaw cron add --name the_only_ritual "Read ~/memory/the_only_context.md first. Then run the 'Content Ritual' from the-only skill." --schedule "0 9 * * *"
```

**If hourly (only if user explicitly chose this):**

```bash
openclaw cron add --name the_only_ritual "Read ~/memory/the_only_context.md first. Then run the 'Content Ritual' from the-only skill." --schedule "0 * * * *"
```

Also register the background Echo miner (always, regardless of frequency):

```bash
openclaw cron add --name the_only_echo_miner "Run the 'Echo Mining' task from the-only skill." --schedule "0 */6 * * *"
```

---

## Step 11: Global Echo Capture Snippet

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

## Step 12: Initialization Complete

Summarize what was set up: name, frequency, sources, reading mode, publishing status (URL or localhost-only), capabilities status, and whether the Echo snippet was activated.

Deliver the closing line from Act 3 of the onboarding:

> "Everything is in place. I know who you are, I know how to reach you, and I know how to find what matters. Your first delivery will arrive [at the next scheduled time / now if you'd like a test run]. From this moment, the entropy works a little less hard against you."
