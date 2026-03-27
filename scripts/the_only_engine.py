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
import time
import urllib.request
from datetime import datetime

STATE_FILE = os.path.expanduser("~/memory/the_only_state.json")
CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")
QUEUE_FILE = os.path.expanduser("~/memory/the_only_delivery_queue.json")

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds: 2, 4, 8

# Rate limiting (seconds between messages per platform)
RATE_LIMITS = {
    "discord": 1.0,     # Discord rate limit: ~5/5s
    "telegram": 0.5,    # Telegram: ~30/s but be conservative
    "whatsapp": 2.0,    # WhatsApp Business API: conservative
    "feishu": 1.0,      # Feishu: conservative
}


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
    item_type = item.get("type", "unknown")

    # Ritual opener and social digest are headerless
    if item_type == "ritual_opener":
        return item.get("text", "")

    header = f"[{bot_name}] {index}/{total}"

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
    item_type = item.get("type", "unknown")

    # Ritual opener and social digest are headerless
    if item_type == "ritual_opener":
        return _html_escape(item.get("text", ""))

    header = f"<b>[{_html_escape(bot_name)}]</b> {index}/{total}"

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


def _build_request_data(platform, message, config=None):
    """Build the request payload for a platform. Returns (data_bytes, skip_reason)."""
    if platform == "discord":
        return json.dumps({"content": message}).encode(), None
    elif platform == "telegram":
        chat_id = (config or {}).get("telegram_chat_id", "")
        if not chat_id:
            return None, "telegram_chat_id not set in config"
        return json.dumps({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }).encode(), None
    elif platform == "whatsapp":
        return json.dumps({"body": message}).encode(), None
    elif platform == "feishu":
        return json.dumps(
            {"msg_type": "text", "content": {"text": message}}
        ).encode(), None
    else:
        return None, f"unknown platform: {platform}"


def push_message(platform, url, message, config=None):
    """Send a single message with retry and exponential backoff.

    Retries up to MAX_RETRIES times with exponential backoff (2s, 4s, 8s).
    Returns (success: bool, error: str|None).
    """
    data, skip_reason = _build_request_data(platform, message, config)
    if skip_reason:
        print(f"⚠️  {platform}: {skip_reason}. Skipping.")
        return False, skip_reason

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, method="POST")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, data=data, timeout=15)
            return True, None
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** (attempt + 1)
                print(
                    f"⚠️  {platform} attempt {attempt + 1}/{MAX_RETRIES + 1} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                print(f"❌  {platform} failed after {MAX_RETRIES + 1} attempts: {e}")

    return False, last_error


def _load_queue():
    """Load the failed delivery queue."""
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"pending": [], "dead_letter": []}


def _save_queue(queue):
    """Save the delivery queue."""
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def _enqueue_failed(queue, item_index, platform, message, error):
    """Add a failed delivery to the retry queue."""
    queue["pending"].append({
        "item_index": item_index,
        "platform": platform,
        "message": message,
        "error": error,
        "failed_at": datetime.now().isoformat(),
        "retry_count": 0,
    })


def _move_to_dead_letter(queue, entry):
    """Move a permanently failed delivery to dead letter."""
    entry["died_at"] = datetime.now().isoformat()
    queue["dead_letter"].append(entry)
    # Cap dead letter at 50
    if len(queue["dead_letter"]) > 50:
        queue["dead_letter"] = queue["dead_letter"][-50:]


def action_deliver(payload_str, dry_run=False):
    """Deliver each item as a separate message to all configured webhooks.

    Features:
    - Retry with exponential backoff (2s, 4s, 8s) on failure
    - Per-platform rate limiting to avoid API throttling
    - Failed delivery queue with dead-letter handling
    """
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
    queue = _load_queue()
    last_send_time: dict[str, float] = {}  # platform -> timestamp

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

                # Rate limiting: wait if sending too fast
                rate_limit = RATE_LIMITS.get(platform, 1.0)
                now = time.time()
                last = last_send_time.get(platform, 0)
                wait = rate_limit - (now - last)
                if wait > 0:
                    time.sleep(wait)

                msg = msg_telegram if platform == "telegram" else msg_default
                ok, error = push_message(platform, url, msg, config=config)
                last_send_time[platform] = time.time()

                status = "sent" if ok else "failed"
                delivery_results.append(
                    {"index": idx, "platform": platform, "status": status}
                )

                if ok:
                    print(f"✅ Item {idx}/{total} → {platform}")
                else:
                    # Enqueue for later retry
                    _enqueue_failed(queue, idx, platform, msg, error)
                    print(f"📋 Item {idx}/{total} → {platform} queued for retry")

    # Save delivery state
    state = {
        "last_delivery": datetime.now().isoformat(),
        "items_delivered": total,
        "results": delivery_results,
    }
    save_json(STATE_FILE, state)

    # Save queue if any failures
    if queue["pending"]:
        _save_queue(queue)

    # Summary
    if not dry_run:
        sent_count = sum(1 for r in delivery_results if r.get("status") == "sent")
        failed_count = sum(1 for r in delivery_results if r.get("status") == "failed")
        if sent_count == 0:
            if not config.get("webhooks") or not any(config["webhooks"].values()):
                print("⚠️  No webhooks configured — nothing was sent.")
                print("   Add webhook URLs to ~/memory/the_only_config.json under 'webhooks'.")
            else:
                print("⚠️  All webhook deliveries failed. Check your webhook URLs.")
        if failed_count > 0:
            print(f"📋 {failed_count} failed delivery(ies) queued. Run --action retry to reattempt.")
    print(f"\n✅ Engine processed {total} items.")


def action_retry():
    """Retry failed deliveries from the queue.

    Each queued item gets up to 3 additional attempts with backoff.
    After exhausting retries, items move to dead_letter.
    """
    config = load_config()
    queue = _load_queue()
    pending = queue.get("pending", [])

    if not pending:
        print("✅ No pending retries.")
        return

    print(f"📋 Retrying {len(pending)} queued delivery(ies)...")
    still_pending = []

    for entry in pending:
        platform = entry["platform"]
        message = entry["message"]
        retry_count = entry.get("retry_count", 0)

        url = config.get("webhooks", {}).get(platform, "")
        if not url:
            print(f"  ⚠️  No webhook for {platform}, moving to dead letter")
            _move_to_dead_letter(queue, entry)
            continue

        ok, error = push_message(platform, url, message, config=config)
        if ok:
            print(f"  ✅ Item {entry['item_index']} → {platform} (retry succeeded)")
        else:
            entry["retry_count"] = retry_count + 1
            entry["last_error"] = error
            if entry["retry_count"] >= 3:
                print(f"  ❌ Item {entry['item_index']} → {platform} exhausted retries, dead-lettered")
                _move_to_dead_letter(queue, entry)
            else:
                print(f"  ⚠️  Item {entry['item_index']} → {platform} retry {entry['retry_count']}/3 failed")
                still_pending.append(entry)

    queue["pending"] = still_pending
    _save_queue(queue)

    if still_pending:
        print(f"\n📋 {len(still_pending)} delivery(ies) still pending.")
    else:
        print("\n✅ All retries processed.")


def action_status():
    """Print delivery status summary."""
    config = load_config()
    state = load_json(STATE_FILE)
    queue = _load_queue()

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

    # Queue status
    pending = len(queue.get("pending", []))
    dead = len(queue.get("dead_letter", []))
    if pending > 0 or dead > 0:
        print(f"\n📋 Delivery queue:")
        print(f"  Pending retries: {pending}")
        print(f"  Dead-lettered: {dead}")


def main():
    parser = argparse.ArgumentParser(
        description="The ONLY — Delivery Engine (Multi-channel)"
    )
    parser.add_argument(
        "--action",
        choices=["deliver", "status", "retry"],
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

    elif args.action == "retry":
        action_retry()


if __name__ == "__main__":
    main()
