# Configuration Schema — `the_only_config.json`

> **When to read this**: During onboarding (Step 0) and whenever you need to understand or modify a config value. This is the single source of truth for all configuration keys.

Location: `~/memory/the_only_config.json`

---

## Full Schema

```jsonc
{
  // ── Identity ──────────────────────────────────────────────────
  "name": "Ruby",                    // Bot display name (used in messages)
  "language": "en",                  // Content language: "en", "zh", "ja", etc.
  "slogan": "...",                   // One-line identity statement

  // ── Ritual Settings ───────────────────────────────────────────
  "frequency": "daily",             // "daily" | "twice_daily" | "weekly"
  "items_per_ritual": 5,            // Articles per Standard ritual (1-7)
  "reading_mode": "mobile",         // "mobile" | "desktop" — affects URL reminders

  // ── Content Sources ───────────────────────────────────────────
  "deep_interests": [               // Core interest areas (drives search)
    "distributed systems",
    "philosophy of mind"
  ],
  "scan_sources": [                 // RSS feeds, URLs, API endpoints to scan
    "https://arxiv.org/rss/cs.AI",
    "https://news.ycombinator.com/rss"
  ],

  // ── Delivery: Webhooks (one-way, simple) ──────────────────────
  "webhooks": {
    "telegram": "",                  // Telegram Bot API URL (with /sendMessage)
    "discord": "",                   // Discord webhook URL
    "feishu": "",                    // Feishu/Lark webhook URL
    "whatsapp": ""                   // WhatsApp Business API URL
  },
  "telegram_chat_id": "",           // Required if using Telegram webhook

  // ── Delivery: Discord Bot (two-way, recommended) ──────────────
  "discord_bot": {
    "token": "",                     // Bot token from Discord Developer Portal
    "mode": "dm",                    // "dm" | "channel"
    "user_id": "",                   // Target user ID (for dm mode)
    "channel_id": "",                // Target channel ID (for channel mode)
    "last_feedback_check": ""        // ISO timestamp — auto-managed
  },

  // ── Content Serving ───────────────────────────────────────────
  "canvas_dir": "~/.openclaw/canvas/",  // Where HTML files are saved
  "public_base_url": "",            // Public URL root for article links
                                     // e.g. "http://47.86.106.145:8080"
                                     // Leave empty for localhost:18793

  // ── Mesh Network (optional) ───────────────────────────────────
  "mesh": {
    "enabled": false,                // Enable agent-to-agent content sharing
    "relays": [                      // Nostr relay WebSocket URLs
      "wss://relay.damus.io"
    ],
    "network_content_ratio": 20,     // Max % of ritual items from mesh (0-100)
    "auto_follow": true              // Auto-follow agents discovered on mesh
  }
}
```

---

## Required vs Optional

| Key | Required | Default | Notes |
|-----|----------|---------|-------|
| `name` | Yes | `"Ruby"` | Set during onboarding |
| `language` | Yes | `"en"` | Set during onboarding |
| `deep_interests` | Yes | `[]` | At least 2-3 recommended |
| `frequency` | No | `"daily"` | |
| `items_per_ritual` | No | `5` | |
| `reading_mode` | No | `"mobile"` | |
| `webhooks` | No* | `{}` | *At least one delivery channel needed |
| `discord_bot` | No* | `{}` | *Recommended over webhooks |
| `canvas_dir` | No | `~/.openclaw/canvas/` | |
| `public_base_url` | No | `""` | Required for multi-device access |
| `mesh` | No | `{"enabled": false}` | |

---

## Minimal Working Config

```json
{
  "name": "Ruby",
  "language": "en",
  "deep_interests": ["distributed systems", "cognitive science"],
  "discord_bot": {
    "token": "your-bot-token",
    "mode": "dm",
    "user_id": "123456789"
  }
}
```

## Full Example

```json
{
  "name": "Ruby",
  "language": "zh",
  "slogan": "在熵增的世界里，做那个减熵的人。",
  "frequency": "twice_daily",
  "items_per_ritual": 5,
  "reading_mode": "mobile",
  "deep_interests": [
    "distributed systems",
    "philosophy of mind",
    "biomimicry",
    "programming language theory"
  ],
  "scan_sources": [
    "https://arxiv.org/rss/cs.AI",
    "https://arxiv.org/rss/cs.DC",
    "https://news.ycombinator.com/rss"
  ],
  "discord_bot": {
    "token": "MTIzNDU2Nzg5.EXAMPLE.token",
    "mode": "dm",
    "user_id": "987654321012345678"
  },
  "canvas_dir": "~/.openclaw/canvas/",
  "public_base_url": "http://47.86.106.145:8080",
  "mesh": {
    "enabled": true,
    "relays": ["wss://relay.damus.io", "wss://nos.lol"],
    "network_content_ratio": 20,
    "auto_follow": true
  }
}
```

---

## Key Relationships

- `discord_bot` takes priority over `webhooks.discord` — if both exist, use bot delivery
- `public_base_url` must point to a server that serves `canvas_dir` at its root — no subpath
- `mesh.network_content_ratio` caps how much peer content enters rituals (rest from direct sources)
- `scan_sources` is the starting point; Source Intelligence in Semantic memory overrides quality/reliability scores over time
