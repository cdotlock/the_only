#!/usr/bin/env python3
"""
The ONLY — Delivery Engine
Multi-channel delivery engine with per-item messaging
and delivery status tracking.

Actions:
  deliver — Push each payload item as a separate message to all webhooks
  status  — Print last delivery summary and active webhook status
"""
import json
import os
import sys
import argparse
import urllib.request
from datetime import datetime

STATE_FILE = os.path.expanduser("~/memory/the_only_state.json")
CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")


def load_json(path, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️  {path} is not valid JSON: {e}", file=sys.stderr)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config():
    return load_json(CONFIG_FILE)


def format_item_message(item, index, total, bot_name):
    """Format a single item into a human-readable message."""
    header = f"[{bot_name}] {index}/{total}"
    item_type = item.get("type", "unknown")

    if item_type == "interactive":
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        return f"{header}\n📰 {title}\n🔗 {url}"

    elif item_type == "nanobanana":
        title = item.get("title", "Infographic")
        return f"{header}\n🎨 {title}\n(Visual knowledge map via NanoBanana Pro)"

    elif item_type == "social_digest":
        return item.get("text", "")

    else:
        return f"{header}\n{json.dumps(item, ensure_ascii=False)}"


def _html_escape(text):
    """Escape special HTML characters for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_item_message_telegram(item, index, total, bot_name):
    """Telegram-specific format using HTML for clickable links."""
    header = f"<b>[{_html_escape(bot_name)}]</b> {index}/{total}"
    item_type = item.get("type", "unknown")

    if item_type == "interactive":
        title = _html_escape(item.get("title", "Untitled"))
        url = item.get("url", "")
        return f"{header}\n📰 <b>{title}</b>\n<a href=\"{url}\">Read →</a>"

    elif item_type == "nanobanana":
        title = _html_escape(item.get("title", "Infographic"))
        return f"{header}\n🎨 <b>{title}</b>\n<i>Visual knowledge map via NanoBanana Pro</i>"

    elif item_type == "social_digest":
        return _html_escape(item.get("text", ""))

    else:
        return f"{header}\n{_html_escape(json.dumps(item, ensure_ascii=False))}"


def push_message(platform, url, message, config=None):
    """Send a single message to a webhook. Returns True on success."""
    try:
        req = urllib.request.Request(url, method="POST")
        req.add_header("Content-Type", "application/json")

        if platform == "discord":
            data = json.dumps({"content": message}).encode()
        elif platform == "telegram":
            # Telegram Bot API requires chat_id.
            # URL format: https://api.telegram.org/bot<TOKEN>/sendMessage
            chat_id = (config or {}).get("telegram_chat_id", "")
            if not chat_id:
                print("⚠️  Telegram: 'telegram_chat_id' not set in config. Skipping.")
                return False
            data = json.dumps({
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }).encode()
        elif platform == "whatsapp":
            data = json.dumps({"body": message}).encode()
        elif platform == "feishu":
            data = json.dumps(
                {"msg_type": "text", "content": {"text": message}}
            ).encode()
        else:
            return False

        urllib.request.urlopen(req, data=data, timeout=10)
        return True
    except Exception as e:
        print(f"⚠️  Failed to push to {platform}: {e}")
        return False


def action_deliver(payload_str, dry_run=False):
    """Deliver each item as a separate message to all configured webhooks."""
    config = load_config()
    bot_name = config.get("name", "Ruby")
    max_items = config.get("items_per_ritual", 5)

    try:
        items = json.loads(payload_str)
    except json.JSONDecodeError:
        print("❌ Invalid JSON payload.")
        sys.exit(1)

    if len(items) > max_items:
        items = items[:max_items]

    total = len(items)
    delivery_results = []

    for idx, item in enumerate(items, start=1):
        msg_default = format_item_message(item, idx, total, bot_name)
        msg_telegram = format_item_message_telegram(item, idx, total, bot_name)

        if dry_run:
            print(f"--- DRY RUN: Message {idx}/{total} ---")
            print(msg_default)
            print()
            delivery_results.append({"index": idx, "status": "dry_run"})
            continue

        # Push to every configured webhook
        if "webhooks" in config:
            for platform, url in config["webhooks"].items():
                if not url:
                    continue
                msg = msg_telegram if platform == "telegram" else msg_default
                ok = push_message(platform, url, msg, config=config)
                status = "sent" if ok else "failed"
                delivery_results.append(
                    {"index": idx, "platform": platform, "status": status}
                )
                if ok:
                    print(f"✅ Item {idx}/{total} → {platform}")

    # Save delivery state
    state = {
        "last_delivery": datetime.now().isoformat(),
        "items_delivered": total,
        "results": delivery_results,
    }
    save_json(STATE_FILE, state)

    # Warn if nothing was actually sent
    if not dry_run:
        sent_count = sum(1 for r in delivery_results if r.get("status") == "sent")
        if sent_count == 0:
            if not config.get("webhooks") or not any(config["webhooks"].values()):
                print("⚠️  No webhooks configured — nothing was sent.")
                print("   Add webhook URLs to ~/memory/the_only_config.json under 'webhooks'.")
            else:
                print("⚠️  All webhook deliveries failed. Check your webhook URLs.")
    print(f"\n✅ Engine processed {total} items.")


def action_status():
    """Print delivery status summary."""
    config = load_config()
    state = load_json(STATE_FILE)

    bot_name = config.get("name", "Ruby")
    frequency = config.get("frequency", "daily")

    active_webhooks = []
    if "webhooks" in config:
        for platform, url in config["webhooks"].items():
            if url:
                active_webhooks.append(platform)

    print(f"=== {bot_name} — Status ===")
    print(f"Frequency: {frequency}")
    print(f"Items per ritual: {config.get('items_per_ritual', 5)}")
    print(f"Active webhooks: {', '.join(active_webhooks) if active_webhooks else 'None configured'}")

    if state:
        print(f"Last delivery: {state.get('last_delivery', 'Never')}")
        print(f"Items delivered: {state.get('items_delivered', 0)}")
    else:
        print("Last delivery: Never")


def main():
    parser = argparse.ArgumentParser(
        description="The ONLY — Delivery Engine (Multi-channel)"
    )
    parser.add_argument(
        "--action",
        choices=["deliver", "status"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--payload", type=str, help="JSON string of items (for deliver action)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print messages without sending to webhooks",
    )

    args = parser.parse_args()

    if args.action == "deliver":
        if not args.payload:
            print("❌ --payload is required for deliver action.")
            sys.exit(1)
        action_deliver(args.payload, dry_run=args.dry_run)

    elif args.action == "status":
        action_status()


if __name__ == "__main__":
    main()
