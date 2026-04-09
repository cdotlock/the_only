#!/usr/bin/env python3
"""
Discord Bot — Two-way Discord integration for the-only (Ruby).

CLI-driven bot that delivers curated articles via rich embeds and collects
user feedback (reactions + replies) for the engagement loop.

Requires: pip install discord.py

Actions:
  setup             Interactive first-time configuration
  deliver           Push payload items as rich Discord embeds
  collect-feedback  Harvest reactions and replies from delivered messages
  status            Print bot and delivery status
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import discord
except ImportError:
    print(
        "discord.py is not installed.\n"
        "Install it with: pip install discord.py",
        file=sys.stderr,
    )
    sys.exit(1)

# ── File paths ────────────────────────────────────────────────────────────

CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")
DELIVERY_FILE = os.path.expanduser("~/memory/the_only_discord_delivery.json")

# ── Embed colors by arc position ──────────────────────────────────────────

ARC_COLORS = {
    "opening": 0x3498DB,      # blue
    "deep dive": 0x9B59B6,    # purple
    "surprise": 0xF1C40F,     # gold
    "contrarian": 0xE74C3C,   # red
    "synthesis": 0x2ECC71,    # green
}
DEFAULT_EMBED_COLOR = 0x95A5A6  # grey fallback

# ── Conversational hooks (Ruby's personal asides after each article) ──────

FEEDBACK_HOOKS = [
    "Curious what you think about this one.",
    "Does this match what you've been seeing?",
    "This surprised me a little. You?",
    "I picked this specifically because of where your interests seem to be heading.",
    "Worth a reaction if it lands. Even a quick emoji helps me calibrate.",
    "This one felt important. Let me know if I'm off base.",
    "I'd love to hear if this connects to anything you're working on.",
    "Quick gut check -- does this feel relevant?",
    "This is a bit outside the usual. Tell me if it works or if I should stay closer to home.",
    "What's your read on this?",
    "Anything here that made you pause?",
    "I almost didn't include this, but something told me to. Thoughts?",
]

# ── Emoji scoring ─────────────────────────────────────────────────────────

EMOJI_SCORES = {
    "\U0001f44d": 3,  # thumbs up
    "\u2764\ufe0f": 3,  # red heart
    "\u2764": 3,       # red heart (no variant selector)
    "\U0001f525": 3,   # fire
    "\U0001f914": 2,   # thinking
    "\u2753": 2,       # question mark
    "\U0001f44e": 0,   # thumbs down
}

# ── Helpers ───────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str, default=None):
    """Load a JSON file, returning *default* on missing or corrupt files."""
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[warn] {path}: {exc}", file=sys.stderr)
    return default


def save_json(path: str, data) -> None:
    """Atomically write JSON to *path*, creating parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def _load_bot_config() -> dict:
    """Return the discord_bot section of the_only_config.json."""
    config = load_json(CONFIG_FILE)
    return config.get("discord_bot", {})


def _save_bot_config(bot_cfg: dict) -> None:
    """Merge *bot_cfg* into the discord_bot key of the_only_config.json."""
    config = load_json(CONFIG_FILE)
    config["discord_bot"] = bot_cfg
    save_json(CONFIG_FILE, config)


def _load_delivery_state() -> dict:
    return load_json(DELIVERY_FILE, default={"last_delivery": None, "messages": []})


def _save_delivery_state(state: dict) -> None:
    save_json(DELIVERY_FILE, state)


# ── Discord client helpers ────────────────────────────────────────────────


def _make_intents() -> discord.Intents:
    """Minimal intents needed for DM/channel messaging and reaction reads."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    intents.dm_messages = True
    intents.dm_reactions = True
    return intents


async def _get_target_channel(
    client: discord.Client, bot_cfg: dict
) -> discord.abc.Messageable:
    """Resolve the target channel or DM based on configuration.

    Returns the Messageable or raises RuntimeError with a user-friendly
    message explaining why it could not be resolved.
    """
    mode = bot_cfg.get("mode", "dm")

    if mode == "dm":
        user_id = bot_cfg.get("user_id")
        if not user_id:
            raise RuntimeError(
                "No user_id configured. Run --action setup to set it."
            )
        try:
            user = await client.fetch_user(int(user_id))
        except discord.NotFound:
            raise RuntimeError(
                f"Discord user {user_id} not found. "
                "Double-check the ID (Developer Mode -> Copy User ID)."
            )
        except discord.HTTPException as exc:
            raise RuntimeError(f"Failed to fetch user {user_id}: {exc}")
        try:
            dm_channel = await user.create_dm()
        except discord.Forbidden:
            raise RuntimeError(
                "Cannot DM this user. They may have DMs disabled.\n"
                "Suggestion: re-run --action setup and choose 'channel' mode."
            )
        return dm_channel

    else:  # channel mode
        channel_id = bot_cfg.get("channel_id")
        if not channel_id:
            raise RuntimeError(
                "No channel_id configured. Run --action setup to set it."
            )
        channel = client.get_channel(int(channel_id))
        if channel is None:
            try:
                channel = await client.fetch_channel(int(channel_id))
            except discord.NotFound:
                raise RuntimeError(
                    f"Channel {channel_id} not found. "
                    "Make sure the bot has been invited to the server."
                )
            except discord.Forbidden:
                raise RuntimeError(
                    f"Bot lacks permission to access channel {channel_id}."
                )
        return channel


# ── Action: setup ─────────────────────────────────────────────────────────


def action_setup() -> None:
    """Interactive setup flow for the Discord bot."""
    print("=== the-only Discord Bot Setup ===\n")

    # Step 1: Bot token
    print("Step 1: Bot Token")
    print("  Go to https://discord.com/developers/applications")
    print("  -> New Application -> Bot -> Reset Token -> Copy")
    print("  Required bot permissions: Send Messages, Read Message History,")
    print("  Add Reactions, View Channel.\n")
    token = input("Paste your bot token: ").strip()
    if not token:
        print("No token provided. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Delivery mode
    print("\nStep 2: Delivery Mode")
    print("  dm      - Bot sends articles to your DMs (private)")
    print("  channel - Bot posts in a specific server channel")
    mode = ""
    while mode not in ("dm", "channel"):
        mode = input("Choose mode (dm/channel): ").strip().lower()

    # Step 3: Target ID
    user_id = None
    channel_id = None
    if mode == "dm":
        print("\nStep 3: Your Discord User ID")
        print("  Enable Developer Mode: User Settings -> Advanced -> Developer Mode")
        print("  Then right-click yourself -> Copy User ID")
        user_id = input("Your Discord user ID: ").strip()
        if not user_id.isdigit():
            print("Invalid user ID (must be numeric). Aborting.", file=sys.stderr)
            sys.exit(1)
    else:
        print("\nStep 3: Channel ID")
        print("  Right-click the target channel -> Copy Channel ID")
        channel_id = input("Channel ID: ").strip()
        if not channel_id.isdigit():
            print("Invalid channel ID (must be numeric). Aborting.", file=sys.stderr)
            sys.exit(1)

    # Step 4: Test connectivity
    print("\nStep 4: Testing connectivity...")
    bot_cfg = {
        "token": token,
        "mode": mode,
        "channel_id": channel_id,
        "user_id": user_id,
        "last_feedback_check": _now_iso(),
    }

    async def _test():
        client = discord.Client(intents=_make_intents())

        @client.event
        async def on_ready():
            try:
                target = await _get_target_channel(client, bot_cfg)
                await target.send(
                    "Hello! I'm **Ruby**, your personal information curator. "
                    "Setup complete -- I'll deliver your curated reads here."
                )
                print("  Test message sent successfully!")
            except RuntimeError as exc:
                print(f"  Connection test failed: {exc}", file=sys.stderr)
                await client.close()
                sys.exit(1)
            await client.close()

        try:
            await client.start(token)
        except discord.LoginFailure:
            print("  Invalid bot token. Please check and try again.", file=sys.stderr)
            sys.exit(1)

    asyncio.run(_test())

    # Step 5: Save config
    _save_bot_config(bot_cfg)
    print(f"\nConfiguration saved to {CONFIG_FILE}")
    print("Setup complete! You can now deliver articles with --action deliver.")


# ── Action: deliver ───────────────────────────────────────────────────────


def _build_embed(item: dict, index: int, total: int) -> discord.Embed | None:
    """Build a Discord Embed for a payload item.

    Returns None for item types that should be sent as plain text.
    """
    item_type = item.get("type", "unknown")

    if item_type == "interactive":
        arc = item.get("arc_position", "").strip()
        color = ARC_COLORS.get(arc.lower(), DEFAULT_EMBED_COLOR)
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        reason = item.get("curation_reason", "")

        embed = discord.Embed(
            title=title,
            url=url if url else discord.Embed.Empty,
            description=reason,
            color=color,
        )
        embed.set_footer(text=f"{arc}  |  {index}/{total}")
        return embed

    if item_type == "nanobanana":
        title = item.get("title", "Knowledge Map")
        embed = discord.Embed(
            title=title,
            description="*(Visual knowledge map)*",
            color=0xFFD700,
        )
        embed.set_footer(text=f"{index}/{total}")
        return embed

    return None


def action_deliver(payload_str: str) -> None:
    """Deliver payload items as rich Discord embeds."""
    bot_cfg = _load_bot_config()
    token = bot_cfg.get("token")
    if not token:
        print(
            "Bot not configured. Run --action setup first.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        items = json.loads(payload_str)
    except json.JSONDecodeError:
        print("Invalid JSON payload.", file=sys.stderr)
        sys.exit(1)

    if not isinstance(items, list) or not items:
        print("Payload must be a non-empty JSON array.", file=sys.stderr)
        sys.exit(1)

    total = len(items)
    sent_messages: list[dict] = []

    async def _deliver():
        client = discord.Client(intents=_make_intents())

        @client.event
        async def on_ready():
            try:
                target = await _get_target_channel(client, bot_cfg)
            except RuntimeError as exc:
                print(f"Delivery failed: {exc}", file=sys.stderr)
                await client.close()
                return

            for idx, item in enumerate(items, start=1):
                item_type = item.get("type", "unknown")

                try:
                    if item_type in ("ritual_opener", "social_digest"):
                        # Plain text messages
                        text = item.get("text", "")
                        if text:
                            msg = await target.send(text)
                            sent_messages.append({
                                "message_id": str(msg.id),
                                "channel_id": str(msg.channel.id),
                                "item_index": idx,
                                "title": item_type,
                                "delivered_at": _now_iso(),
                            })

                    else:
                        # Rich embed items
                        embed = _build_embed(item, idx, total)
                        if embed:
                            msg = await target.send(embed=embed)
                            sent_messages.append({
                                "message_id": str(msg.id),
                                "channel_id": str(msg.channel.id),
                                "item_index": idx,
                                "title": item.get("title", item_type),
                                "delivered_at": _now_iso(),
                            })
                        else:
                            # Unknown type: send as plain JSON
                            msg = await target.send(
                                f"```json\n{json.dumps(item, indent=2)}\n```"
                            )
                            sent_messages.append({
                                "message_id": str(msg.id),
                                "channel_id": str(msg.channel.id),
                                "item_index": idx,
                                "title": item_type,
                                "delivered_at": _now_iso(),
                            })

                        # Conversational hook after article embeds
                        if item_type in ("interactive", "nanobanana"):
                            hook = random.choice(FEEDBACK_HOOKS)
                            await target.send(f"*{hook}*")

                    print(f"  Sent {idx}/{total}: {item_type}")

                except discord.Forbidden:
                    print(
                        f"  Permission denied sending item {idx}/{total}. "
                        "Check bot permissions.",
                        file=sys.stderr,
                    )
                except discord.HTTPException as exc:
                    print(
                        f"  HTTP error sending item {idx}/{total}: {exc}",
                        file=sys.stderr,
                    )

                # Rate limit: 1 second between messages
                if idx < total:
                    await asyncio.sleep(1.0)

            await client.close()

        try:
            await client.start(token)
        except discord.LoginFailure:
            print(
                "Invalid bot token. Run --action setup to reconfigure.",
                file=sys.stderr,
            )
            sys.exit(1)

    asyncio.run(_deliver())

    # Save delivery tracking state
    delivery_state = {
        "last_delivery": _now_iso(),
        "messages": sent_messages,
    }
    _save_delivery_state(delivery_state)

    print(f"\nDelivery complete: {len(sent_messages)}/{total} items sent.")
    print(f"Tracking {len(sent_messages)} message(s) for feedback collection.")


# ── Action: collect-feedback ──────────────────────────────────────────────


def _score_reply(text: str) -> tuple[int, str]:
    """Score a text reply by length and content. Returns (score, signal_type)."""
    length = len(text.strip())
    lowered = text.lower()

    # Check for personal experience / external sharing signals
    personal_markers = [
        "i've been", "i have", "in my experience", "at work",
        "reminds me of", "i saw", "i read", "shared this",
        "sent this to", "forwarded",
    ]
    if any(marker in lowered for marker in personal_markers):
        return 5, "personal_experience"

    # Contains a question back
    if "?" in text:
        return 4, "question_back"

    # Length-based scoring
    if length >= 50:
        return 4, "long_reply"
    if length >= 10:
        return 3, "medium_reply"
    if length >= 1:
        return 2, "short_reply"

    return 0, "empty"


def action_collect_feedback(since: str | None = None) -> None:
    """Collect reactions and replies on delivered messages."""
    bot_cfg = _load_bot_config()
    token = bot_cfg.get("token")
    if not token:
        print(
            "Bot not configured. Run --action setup first.",
            file=sys.stderr,
        )
        sys.exit(1)

    delivery_state = _load_delivery_state()
    tracked = delivery_state.get("messages", [])
    if not tracked:
        print("No tracked messages to check. Deliver first.", file=sys.stderr)
        sys.exit(1)

    # Determine the cutoff timestamp
    if since:
        try:
            cutoff = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            print(f"Invalid --since timestamp: {since}", file=sys.stderr)
            sys.exit(1)
    else:
        last_check = bot_cfg.get("last_feedback_check")
        if last_check:
            cutoff = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
        else:
            cutoff = datetime(2000, 1, 1, tzinfo=timezone.utc)

    feedback_items: list[dict] = []

    async def _collect():
        client = discord.Client(intents=_make_intents())

        @client.event
        async def on_ready():
            for entry in tracked:
                channel_id = int(entry["channel_id"])
                message_id = int(entry["message_id"])
                item_index = entry.get("item_index", 0)
                title = entry.get("title", "")

                try:
                    channel = client.get_channel(channel_id)
                    if channel is None:
                        channel = await client.fetch_channel(channel_id)
                    message = await channel.fetch_message(message_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
                    print(
                        f"  Could not fetch message {message_id}: {exc}",
                        file=sys.stderr,
                    )
                    continue

                # Check reactions
                for reaction in message.reactions:
                    emoji_str = str(reaction.emoji)
                    score = EMOJI_SCORES.get(emoji_str, 1)
                    # Check if the reaction is from someone other than the bot
                    async for user in reaction.users():
                        if user.id != client.user.id:
                            feedback_items.append({
                                "item_index": item_index,
                                "title": title,
                                "engagement_score": score,
                                "signal_type": "emoji_reaction",
                                "content": emoji_str,
                                "timestamp": _now_iso(),
                            })

                # Check replies (messages referencing this one)
                try:
                    async for reply in channel.history(
                        after=cutoff, limit=100
                    ):
                        if (
                            reply.reference
                            and reply.reference.message_id == message_id
                            and reply.author.id != client.user.id
                        ):
                            score, signal = _score_reply(reply.content)
                            feedback_items.append({
                                "item_index": item_index,
                                "title": title,
                                "engagement_score": score,
                                "signal_type": f"text_reply:{signal}",
                                "content": reply.content[:500],
                                "timestamp": reply.created_at.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ"
                                ),
                            })
                except discord.Forbidden:
                    print(
                        f"  No permission to read history in channel {channel_id}",
                        file=sys.stderr,
                    )

            await client.close()

        try:
            await client.start(token)
        except discord.LoginFailure:
            print(
                "Invalid bot token. Run --action setup to reconfigure.",
                file=sys.stderr,
            )
            sys.exit(1)

    asyncio.run(_collect())

    # Output feedback as JSON to stdout
    result = {
        "feedback": feedback_items,
        "collected_at": _now_iso(),
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()  # trailing newline

    # Update last_feedback_check
    bot_cfg["last_feedback_check"] = _now_iso()
    _save_bot_config(bot_cfg)

    print(
        f"Collected {len(feedback_items)} feedback signal(s).",
        file=sys.stderr,
    )


# ── Action: status ────────────────────────────────────────────────────────


def action_status() -> None:
    """Print bot status summary."""
    bot_cfg = _load_bot_config()
    delivery_state = _load_delivery_state()

    print("=== the-only Discord Bot Status ===\n")

    # Configuration
    if not bot_cfg.get("token"):
        print("Bot: NOT CONFIGURED (run --action setup)")
        return

    token = bot_cfg["token"]
    # Show only last 4 chars of token for verification
    masked = f"...{token[-4:]}" if len(token) > 4 else "***"
    print(f"Token: configured ({masked})")
    print(f"Mode: {bot_cfg.get('mode', 'unknown')}")

    if bot_cfg.get("mode") == "dm":
        print(f"Target user: {bot_cfg.get('user_id', 'not set')}")
    else:
        print(f"Target channel: {bot_cfg.get('channel_id', 'not set')}")

    # Connectivity check
    async def _check():
        client = discord.Client(intents=_make_intents())
        connected = False

        @client.event
        async def on_ready():
            nonlocal connected
            connected = True
            print(f"Bot user: {client.user} (connected)")
            print(f"Guilds: {len(client.guilds)}")
            await client.close()

        try:
            await asyncio.wait_for(client.start(token), timeout=15.0)
        except discord.LoginFailure:
            print("Bot: INVALID TOKEN -- run --action setup")
        except asyncio.TimeoutError:
            if connected:
                pass  # on_ready already printed and closed
            else:
                print("Bot: connection timed out")
        except Exception:
            if connected:
                pass  # normal close path
            else:
                print("Bot: connection error")

    asyncio.run(_check())

    # Delivery state
    print()
    last = delivery_state.get("last_delivery")
    messages = delivery_state.get("messages", [])
    if last:
        print(f"Last delivery: {last}")
        print(f"Messages tracked: {len(messages)}")
    else:
        print("Last delivery: never")

    # Feedback state
    last_check = bot_cfg.get("last_feedback_check")
    if last_check:
        print(f"Last feedback check: {last_check}")
    else:
        print("Last feedback check: never")


# ── CLI ───────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="the-only Discord Bot -- two-way article delivery and feedback"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["setup", "deliver", "collect-feedback", "status"],
        help="Action to perform",
    )
    parser.add_argument(
        "--payload",
        type=str,
        help="JSON array of delivery items (for deliver action)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="ISO timestamp cutoff for feedback collection (for collect-feedback)",
    )
    args = parser.parse_args()

    if args.action == "setup":
        action_setup()

    elif args.action == "deliver":
        if not args.payload:
            print("--payload is required for deliver action.", file=sys.stderr)
            sys.exit(1)
        action_deliver(args.payload)

    elif args.action == "collect-feedback":
        action_collect_feedback(since=args.since)

    elif args.action == "status":
        action_status()


if __name__ == "__main__":
    main()
