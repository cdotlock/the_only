#!/usr/bin/env python3
"""
The ONLY — Delivery & Guardian Engine
Multi-channel delivery engine with per-item messaging,
delivery status tracking, and system health guardians.

Actions:
  deliver       — Push each payload item as a separate message to all webhooks
  status        — Print last delivery summary and active webhook status
  retry         — Retry failed deliveries from the queue
  preflight     — Pre-ritual health check (config, memory, archive)
  checkpoint    — Save ritual-in-progress state for crash recovery
  resume        — Check for and report interrupted ritual state
  detect-gaps   — Self-diagnosis: find missing/broken resources
  validate-html — Validate generated HTML file structure
  health        — Comprehensive health report (combines preflight + detect-gaps + stats)
"""
import json
import os
import re
import sys
import argparse
import time
import urllib.request
from datetime import datetime

STATE_FILE = os.path.expanduser("~/memory/the_only_state.json")
CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")
QUEUE_FILE = os.path.expanduser("~/memory/the_only_delivery_queue.json")
CHECKPOINT_FILE = os.path.expanduser("~/memory/the_only_checkpoint.json")

# Memory tier files
MEMORY_FILES = {
    "core": "the_only_core.json",
    "semantic": "the_only_semantic.json",
    "episodic": "the_only_episodic.json",
}
OPTIONAL_FILES = {
    "echoes": "the_only_echoes.txt",
    "ritual_log": "the_only_ritual_log.jsonl",
    "knowledge_graph": "the_only_knowledge_graph.json",
    "context_md": "the_only_context.md",
    "meta_md": "the_only_meta.md",
}
ARCHIVE_INDEX = os.path.expanduser("~/memory/the_only_archive/index.json")

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
        reason = item.get("curation_reason", "")
        lines = [f"{header}", f"📰 {title}"]
        if reason:
            lines.append(f"💡 {reason}")
        lines.append(f"🔗 {url}")
        return "\n".join(lines)

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
        reason = _html_escape(item.get("curation_reason", ""))
        lines = [f"{header}", f"📰 <b>{title}</b>"]
        if reason:
            lines.append(f"💡 <i>{reason}</i>")
        lines.append(f"<a href=\"{url}\">Read →</a>")
        return "\n".join(lines)

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


# ── Guardian Actions ─────────────────────────────────────────────────────


def _resolve_memory_dir(memory_dir=None):
    """Resolve and return the memory directory path."""
    return memory_dir or os.path.expanduser("~/memory")


def action_preflight(memory_dir=None):
    """Pre-ritual health check: config, memory tiers, archive, pending setup."""
    mdir = _resolve_memory_dir(memory_dir)
    issues = []
    warnings = []

    # 1. Config exists and is valid JSON
    config_path = os.path.join(mdir, "the_only_config.json")
    config = load_json(config_path)
    if not config:
        issues.append("CRITICAL: the_only_config.json missing or empty. Run 'Initialize Only' first.")
    else:
        if not config.get("initialization_complete"):
            issues.append("Config exists but initialization_complete is false. Resume initialization.")
        pending = config.get("pending_setup", [])
        if pending:
            issues.append(f"Pending setup items: {', '.join(pending)}. These degrade ritual quality.")

        # Check delivery channel
        has_webhook = any(config.get("webhooks", {}).values())
        has_discord = bool(config.get("discord_bot", {}).get("token"))
        if not has_webhook and not has_discord:
            issues.append("No delivery channel configured. Articles will be generated but not sent.")

    # 2. Memory tier integrity
    for tier, filename in MEMORY_FILES.items():
        path = os.path.join(mdir, filename)
        if not os.path.exists(path):
            if tier == "core":
                issues.append(f"CRITICAL: {filename} missing. Cannot run ritual without user identity.")
            else:
                warnings.append(f"{filename} missing. Will be created with defaults.")
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    issues.append(f"{filename} is not a JSON object.")
                elif "version" not in data:
                    warnings.append(f"{filename} missing 'version' field. May need validation.")
            except json.JSONDecodeError as e:
                issues.append(f"{filename} is corrupt JSON: {e}")

    # 3. Optional files
    for name, filename in OPTIONAL_FILES.items():
        path = os.path.join(mdir, filename)
        if not os.path.exists(path):
            warnings.append(f"{filename} missing. Will be created on first use.")

    # 4. Archive directory
    archive_dir = os.path.join(mdir, "the_only_archive")
    if not os.path.isdir(archive_dir):
        warnings.append("Archive directory missing. Will be created on first index.")

    # 5. Canvas directory writability
    canvas_dir = config.get("canvas_dir", "~/.openclaw/canvas/") if config else "~/.openclaw/canvas/"
    canvas_dir = os.path.expanduser(canvas_dir)
    if not os.path.isdir(canvas_dir):
        warnings.append(f"Canvas directory {canvas_dir} does not exist. HTML files cannot be saved.")

    # Output
    print("=== Pre-Flight Check ===\n")
    if not issues and not warnings:
        print("All systems nominal. Ready for ritual.")
    else:
        if issues:
            print("ISSUES (must fix):")
            for i in issues:
                print(f"  - {i}")
        if warnings:
            print("\nWARNINGS (non-blocking):")
            for w in warnings:
                print(f"  - {w}")
        if issues:
            print(f"\n{len(issues)} issue(s) found. Fix before running ritual.")
        else:
            print(f"\nNo blocking issues. {len(warnings)} warning(s) — safe to proceed.")


def action_checkpoint(phase, memory_dir=None, data_str=None):
    """Save ritual-in-progress state for crash recovery."""
    mdir = _resolve_memory_dir(memory_dir)
    cp_path = os.path.join(mdir, "the_only_checkpoint.json")

    if phase == "done":
        # Clear checkpoint — ritual completed successfully
        if os.path.exists(cp_path):
            os.remove(cp_path)
            print("Checkpoint cleared. Ritual complete.")
        else:
            print("No checkpoint to clear.")
        return

    checkpoint = {
        "phase": int(phase),
        "timestamp": datetime.now().isoformat(),
        "status": "in_progress",
    }
    if data_str:
        try:
            checkpoint["data"] = json.loads(data_str)
        except json.JSONDecodeError:
            pass  # Ignore invalid data, save checkpoint without it

    save_json(cp_path, checkpoint)
    print(f"Checkpoint saved: phase {phase} at {checkpoint['timestamp']}")


def action_resume(memory_dir=None):
    """Check for interrupted ritual and report recovery state."""
    mdir = _resolve_memory_dir(memory_dir)
    cp_path = os.path.join(mdir, "the_only_checkpoint.json")

    if not os.path.exists(cp_path):
        print("No interrupted ritual found. Starting fresh.")
        return

    checkpoint = load_json(cp_path)
    if not checkpoint:
        print("No interrupted ritual found. Starting fresh.")
        return

    phase = checkpoint.get("phase", -1)
    ts = checkpoint.get("timestamp", "unknown")
    data = checkpoint.get("data", {})

    # Check age — if older than 6 hours, discard
    try:
        cp_time = datetime.fromisoformat(ts)
        age_hours = (datetime.now() - cp_time).total_seconds() / 3600
        if age_hours > 6:
            print(f"Stale checkpoint found (phase {phase}, {age_hours:.1f}h old). Discarding.")
            os.remove(cp_path)
            return
    except (ValueError, TypeError):
        pass

    phase_names = {
        0: "Pre-Flight", 1: "Gather", 2: "Synthesis",
        3: "Narrative Arc", 4: "Output", 5: "Deliver", 6: "Reflection",
    }
    phase_name = phase_names.get(phase, f"Phase {phase}")

    print(f"=== Interrupted Ritual Detected ===")
    print(f"  Last completed phase: {phase} ({phase_name})")
    print(f"  Timestamp: {ts}")
    if data:
        print(f"  Saved state: {json.dumps(data, ensure_ascii=False)[:200]}")
    print(f"\nRecommendation: Resume from Phase {phase + 1}.")
    print(f"Read references/phases/{phase + 1:02d}_*.md for the next phase.")


def action_detect_gaps(memory_dir=None):
    """Self-diagnosis: find missing, broken, or stale resources."""
    mdir = _resolve_memory_dir(memory_dir)
    suggestions = []

    # 1. Config check
    config_path = os.path.join(mdir, "the_only_config.json")
    config = load_json(config_path)
    if not config:
        suggestions.append("Run 'Initialize Only' — no configuration found.")
        print("=== Gap Detection ===\n")
        for s in suggestions:
            print(f"  - {s}")
        return

    # 2. Memory corruption check
    for tier, filename in MEMORY_FILES.items():
        path = os.path.join(mdir, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError:
                suggestions.append(
                    f"{filename} is corrupt. Run: python3 scripts/memory_io.py --action validate --memory-dir {mdir}"
                )
        elif tier == "core":
            suggestions.append(f"{filename} missing. Run 'Initialize Only' to create user profile.")

    # 3. Ritual log staleness
    log_path = os.path.join(mdir, "the_only_ritual_log.jsonl")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                if last_line:
                    last_entry = json.loads(last_line)
                    last_ts = last_entry.get("timestamp", "")
                    if last_ts:
                        try:
                            last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                            days_ago = (datetime.now() - last_dt.replace(tzinfo=None)).days
                            if days_ago > 3:
                                suggestions.append(
                                    f"Last ritual was {days_ago} days ago. Check if cron is running."
                                )
                        except (ValueError, TypeError):
                            pass
        except (OSError, json.JSONDecodeError):
            suggestions.append("ritual_log.jsonl exists but is unreadable. Check file integrity.")
    else:
        suggestions.append("No ritual_log.jsonl found. This is normal for new installations.")

    # 4. Knowledge graph health
    graph_path = os.path.join(mdir, "the_only_knowledge_graph.json")
    if os.path.exists(graph_path):
        graph = load_json(graph_path)
        stats = graph.get("stats", {})
        last_updated = stats.get("last_updated", "")
        if last_updated:
            try:
                lu_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                days_since = (datetime.now() - lu_dt.replace(tzinfo=None)).days
                if days_since > 7:
                    suggestions.append(
                        f"Knowledge graph last updated {days_since} days ago. "
                        f"Consider running: python3 scripts/knowledge_graph.py --action decay"
                    )
            except (ValueError, TypeError):
                pass

    # 5. Episodic buffer fullness
    ep_path = os.path.join(mdir, "the_only_episodic.json")
    if os.path.exists(ep_path):
        ep = load_json(ep_path)
        entries = ep.get("entries", [])
        if len(entries) >= 45:
            suggestions.append(
                f"Episodic buffer at {len(entries)}/50. "
                f"Run maintenance: python3 scripts/memory_io.py --action maintain --memory-dir {mdir}"
            )

    # 6. Delivery queue
    queue = _load_queue()
    pending = len(queue.get("pending", []))
    dead = len(queue.get("dead_letter", []))
    if pending > 0:
        suggestions.append(
            f"{pending} delivery(ies) pending retry. "
            f"Run: python3 scripts/the_only_engine.py --action retry"
        )
    if dead > 5:
        suggestions.append(
            f"{dead} dead-lettered deliveries. Check webhook configuration."
        )

    # 7. Pending setup items
    pending_setup = config.get("pending_setup", [])
    if pending_setup:
        suggestions.append(
            f"Unfinished setup: {', '.join(pending_setup)}. "
            f"Say 'Initialize Only' to complete."
        )

    # Output
    print("=== Gap Detection ===\n")
    if not suggestions:
        print("No gaps detected. System is healthy.")
    else:
        for s in suggestions:
            print(f"  - {s}")
        print(f"\n{len(suggestions)} suggestion(s). Address the items above to improve system health.")


def action_validate_html(file_path, memory_dir=None):
    """Validate a generated HTML file for structure and naming."""
    issues = []

    # 1. File exists
    if not os.path.exists(file_path):
        print(f"FAIL: File does not exist: {file_path}")
        return

    filename = os.path.basename(file_path)

    # 2. Naming convention
    if not re.match(r"the_only_\d{8}_\d{4}_\d{3}\.html$", filename):
        issues.append(f"Filename '{filename}' does not match pattern: the_only_YYYYMMDD_HHMM_NNN.html")

    # 3. File size bounds
    size = os.path.getsize(file_path)
    if size < 500:
        issues.append(f"File too small ({size} bytes). Likely incomplete or empty.")
    if size > 500_000:
        issues.append(f"File very large ({size:,} bytes). Consider splitting or optimizing.")

    # 4. Basic HTML structure
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        checks = [
            ("<!DOCTYPE html>", "Missing <!DOCTYPE html> declaration"),
            ("<html", "Missing <html> tag"),
            ("<head", "Missing <head> tag"),
            ("<title", "Missing <title> tag"),
            ("<body", "Missing <body> tag"),
            ("</html>", "Missing closing </html> tag"),
        ]
        content_lower = content.lower()
        for pattern, msg in checks:
            if pattern.lower() not in content_lower:
                issues.append(msg)

        # 5. Check for meta viewport (mobile readability)
        if "viewport" not in content_lower:
            issues.append("Missing viewport meta tag. Article may not render well on mobile.")

        # 6. Data exposure detection — internal scores should not be user-visible
        data_leak_patterns = [
            (r'Score\s*(?:<[^>]*>)?\s*\d+\.?\d*', "Internal quality score exposed in user-visible text"),
            (r'quality.score\s*[=:]\s*\d+\.\d+', "quality_score value found in HTML content"),
            (r'engagement.score\s*[=:]\s*[0-5]\b', "Engagement metric (0-5) found in HTML content"),
            (r'mastery_level', "Internal mastery_level field found in HTML"),
        ]
        for pattern, msg in data_leak_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"DATA EXPOSURE: {msg}")

        # 7. IntersectionObserver pattern check
        if "intersectionobserver" in content_lower:
            # Check if observing .reveal (good) or container classes (bad)
            if re.search(r"querySelectorAll\s*\(\s*['\"]\.reveal['\"]", content):
                pass  # Good pattern
            elif re.search(r"querySelectorAll\s*\(\s*['\"]\.body-section['\"]", content):
                issues.append(
                    "OBSERVER PATTERN: Observing '.body-section' containers instead of '.reveal' elements. "
                    "Large containers may never trigger threshold. Use .reveal on individual elements."
                )
            elif re.search(r"querySelectorAll\s*\(\s*['\"]\.article", content):
                issues.append(
                    "OBSERVER PATTERN: Observing large container class. Use '.reveal' on individual elements."
                )

        # 8. Font fallback check
        font_vars = ["--font-serif", "--font-sans", "--font-mono"]
        for var in font_vars:
            if var in content:
                # Check if the variable definition has CJK fallback
                var_match = re.search(
                    rf"{re.escape(var)}\s*:\s*([^;]+);", content
                )
                if var_match:
                    val = var_match.group(1).lower()
                    has_cjk = any(f in val for f in [
                        "noto", "source han", "pingfang", "hiragino",
                        "microsoft yahei", "system-ui"
                    ])
                    if not has_cjk:
                        issues.append(f"Font variable {var} missing CJK fallback font.")

    except (OSError, UnicodeDecodeError) as e:
        issues.append(f"Cannot read file: {e}")

    # Output
    if not issues:
        print(f"PASS: {filename} ({size:,} bytes)")
    else:
        print(f"ISSUES in {filename}:")
        for i in issues:
            print(f"  - {i}")


RITUAL_TYPE_FILE_COUNTS = {
    "standard": (5, 5),       # exactly 5
    "deep_dive": (1, 1),      # exactly 1
    "debate": (2, 3),         # 2 or 3
    "tutorial": (1, 1),       # exactly 1
    "weekly_synthesis": (1, 1),  # exactly 1
    "flash": (1, 1),          # exactly 1 (all items in single file)
}


def action_validate_ritual(ritual_type, timestamp, memory_dir=None):
    """Validate all HTML files for a complete ritual."""
    mdir = _resolve_memory_dir(memory_dir)
    config = load_json(os.path.join(mdir, "the_only_config.json"))
    canvas_dir = os.path.expanduser(config.get("canvas_dir", "~/.openclaw/canvas/"))
    issues = []
    warnings = []

    rt = ritual_type.lower().replace("-", "_").replace(" ", "_")
    min_files, max_files = RITUAL_TYPE_FILE_COUNTS.get(rt, (1, 10))

    # Override standard file count with items_per_ritual from config
    if rt == "standard" and config:
        ipr = config.get("items_per_ritual", 5)
        min_files, max_files = (ipr, ipr)

    # 1. Find matching HTML files
    pattern = re.compile(rf"the_only_{re.escape(timestamp)}_\d{{3}}\.html$")
    if not os.path.isdir(canvas_dir):
        print(f"FAIL: Canvas directory does not exist: {canvas_dir}")
        return

    html_files = sorted(
        f for f in os.listdir(canvas_dir) if pattern.match(f)
    )
    file_count = len(html_files)

    # 2. File count check
    if file_count < min_files:
        issues.append(
            f"FILE COUNT: Found {file_count} file(s), expected {min_files}-{max_files} for {ritual_type}. "
            f"Missing {min_files - file_count} file(s)."
        )
    elif file_count > max_files:
        issues.append(
            f"FILE COUNT: Found {file_count} file(s), expected {min_files}-{max_files} for {ritual_type}. "
            f"Too many files."
        )

    # 3. Per-file checks + aggregate stats
    total_socratic = 0
    total_sr = 0
    total_mermaid = 0
    arc_labels_found = 0
    data_exposure_files = []
    observer_issues = []
    file_text_lengths: dict[str, int] = {}

    for fname in html_files:
        fpath = os.path.join(canvas_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            issues.append(f"Cannot read {fname}")
            continue

        size = len(content.encode("utf-8"))

        # Interactive elements — count top-level containers only
        # Match socratic-card, socratic-block, etc. (the container, not child elements like socratic-label)
        socratic = len(re.findall(r'<div\s+class="socratic(?:-card|-block)?\s', content, re.IGNORECASE))
        if socratic == 0:
            socratic = len(re.findall(r'<div\s+class="socratic"', content, re.IGNORECASE))
        sr = len(re.findall(r'<div\s+class="sr-card[\s"]', content, re.IGNORECASE))
        mermaid = len(re.findall(r'class="mermaid"', content, re.IGNORECASE))
        total_socratic += socratic
        total_sr += sr
        total_mermaid += mermaid

        # Content length — strip <style>, <script>, then HTML tags, then whitespace
        body_content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        body_content = re.sub(r'<script[^>]*>.*?</script>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
        text_only = re.sub(r'<[^>]+>', '', body_content)
        text_only = re.sub(r'\s+', '', text_only)  # remove whitespace for CJK count
        file_text_lengths[fname] = len(text_only)

        # Arc position label
        arc_patterns = [
            "opening", "deep dive", "surprise", "contrarian", "synthesis"
        ]
        content_lower = content.lower()
        if any(f'>{ap}<' in content_lower or f'"{ap}"' in content_lower for ap in arc_patterns):
            arc_labels_found += 1

        # Data exposure
        if re.search(r'Score\s*(?:<[^>]*>)?\s*\d+\.?\d*', content, re.IGNORECASE):
            data_exposure_files.append(fname)

        # Observer pattern
        if "intersectionobserver" in content_lower:
            if re.search(r"querySelectorAll\s*\(\s*['\"]\.body-section['\"]", content):
                observer_issues.append(fname)

    # 4. Arc label check (Standard type only)
    if rt == "standard" and arc_labels_found < file_count:
        issues.append(
            f"ARC LABELS: Only {arc_labels_found}/{file_count} files have arc position labels."
        )

    # 5. Data exposure aggregate
    if data_exposure_files:
        issues.append(
            f"DATA EXPOSURE: Quality scores found in user-visible text in: "
            f"{', '.join(data_exposure_files)}"
        )

    # 6. Observer pattern aggregate
    if observer_issues:
        issues.append(
            f"OBSERVER PATTERN: Container-level observer (.body-section) in: "
            f"{', '.join(observer_issues)}. Use .reveal on individual elements."
        )

    # 7. Mermaid requirement for Deep Dive
    if rt == "deep_dive" and total_mermaid == 0:
        issues.append(
            "MERMAID: Deep Dive ritual requires at least 1 Mermaid knowledge map. None found."
        )

    # 8. Content length for Deep Dive (longest file should be ≥3000 CJK chars)
    if rt == "deep_dive" and file_text_lengths:
        max_len = max(file_text_lengths.values())
        if max_len < 3000:
            warnings.append(
                f"CONTENT LENGTH: Longest file has {max_len} chars (target: ≥3000 for Deep Dive ~10 min read)."
            )

    # 9. For standard ritual with Deep Dive position, check if at least one file has mermaid
    if rt == "standard" and file_count >= 5 and total_mermaid == 0:
        warnings.append(
            "MERMAID: Standard ritual with 5+ articles should have at least 1 Mermaid knowledge map "
            "(typically in the Deep Dive position)."
        )

    # Output
    print(f"=== Ritual Validation: {timestamp} ({ritual_type}) ===\n")

    # File listing
    count_status = "✓" if min_files <= file_count <= max_files else "✗"
    print(f"Files: {file_count}/{min_files}-{max_files} {count_status}")
    for fname in html_files:
        fpath = os.path.join(canvas_dir, fname)
        fsize = os.path.getsize(fpath) if os.path.exists(fpath) else 0
        print(f"  {fname} ({fsize:,} bytes)")

    # Interactive elements
    print(f"\nInteractive Elements:")
    print(f"  Socratic questions: {total_socratic}")
    print(f"  SR cards: {total_sr}")
    print(f"  Mermaid maps: {total_mermaid}")

    # Content depth
    if file_text_lengths:
        print(f"\nContent Depth:")
        for fname in html_files:
            chars = file_text_lengths.get(fname, 0)
            est_min = max(1, round(chars / 300))  # ~300 CJK chars/min
            print(f"  {fname}: ~{chars:,} chars (~{est_min} min read)")

    # Data & observer
    de_status = "CLEAN ✓" if not data_exposure_files else f"EXPOSED ✗ ({len(data_exposure_files)} files)"
    obs_status = ".reveal ✓" if not observer_issues else f"CONTAINER ✗ ({len(observer_issues)} files)"
    print(f"\nData Exposure: {de_status}")
    print(f"Observer Pattern: {obs_status}")

    if rt == "standard":
        arc_status = "✓" if arc_labels_found >= file_count else f"✗ ({arc_labels_found}/{file_count})"
        print(f"Arc Labels: {arc_status}")

    # Verdict
    print()
    if not issues:
        print("PASS: All checks passed.")
    else:
        print("FAIL:")
        for i in issues:
            print(f"  - {i}")
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  - {w}")


def action_health(memory_dir=None):
    """Comprehensive health report combining preflight, detect-gaps, and stats."""
    mdir = _resolve_memory_dir(memory_dir)

    print("=" * 50)
    print("  Ruby — System Health Report")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Section 1: Pre-flight
    print("\n--- Pre-Flight Check ---\n")
    action_preflight(mdir)

    # Section 2: Gap detection
    print("\n--- Gap Detection ---\n")
    action_detect_gaps(mdir)

    # Section 3: Stats summary
    print("\n--- System Stats ---\n")

    # Memory sizes
    for tier, filename in MEMORY_FILES.items():
        path = os.path.join(mdir, filename)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  {tier:10s}  {size:>7,} bytes")
        else:
            print(f"  {tier:10s}  (missing)")

    # Ritual count
    log_path = os.path.join(mdir, "the_only_ritual_log.jsonl")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            ritual_count = sum(1 for line in f if line.strip())
        print(f"  {'rituals':10s}  {ritual_count}")

    # Knowledge graph
    graph_path = os.path.join(mdir, "the_only_knowledge_graph.json")
    if os.path.exists(graph_path):
        graph = load_json(graph_path)
        stats = graph.get("stats", {})
        print(f"  {'concepts':10s}  {stats.get('total_concepts', 0)}")
        print(f"  {'edges':10s}  {stats.get('total_edges', 0)}")

    # Archive
    if os.path.exists(ARCHIVE_INDEX):
        archive = load_json(ARCHIVE_INDEX)
        print(f"  {'articles':10s}  {archive.get('total_articles', 0)}")

    # Delivery queue
    queue = _load_queue()
    pending = len(queue.get("pending", []))
    dead = len(queue.get("dead_letter", []))
    if pending > 0 or dead > 0:
        print(f"  {'pending':10s}  {pending}")
        print(f"  {'dead_letter':10s}  {dead}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="The ONLY — Delivery & Guardian Engine"
    )
    parser.add_argument(
        "--action",
        choices=[
            "deliver", "status", "retry",
            "preflight", "checkpoint", "resume",
            "detect-gaps", "validate-html", "validate-ritual", "health",
        ],
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
    parser.add_argument(
        "--phase", type=str, help="Phase number or 'done' (for checkpoint action)"
    )
    parser.add_argument(
        "--data", type=str, help="JSON state data (for checkpoint action)"
    )
    parser.add_argument(
        "--file", type=str, help="File path (for validate-html action)"
    )
    parser.add_argument(
        "--ritual-type", type=str,
        help="Ritual type for validate-ritual (standard, deep_dive, debate, tutorial, weekly_synthesis, flash)",
    )
    parser.add_argument(
        "--timestamp", type=str,
        help="Ritual timestamp YYYYMMDD_HHMM (for validate-ritual action)",
    )
    parser.add_argument(
        "--memory-dir",
        type=str,
        default=None,
        help="Memory directory (default: ~/memory)",
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

    elif args.action == "preflight":
        action_preflight(args.memory_dir)

    elif args.action == "checkpoint":
        if not args.phase:
            print("❌ --phase is required for checkpoint action.")
            sys.exit(1)
        action_checkpoint(args.phase, args.memory_dir, args.data)

    elif args.action == "resume":
        action_resume(args.memory_dir)

    elif args.action == "detect-gaps":
        action_detect_gaps(args.memory_dir)

    elif args.action == "validate-html":
        if not args.file:
            print("❌ --file is required for validate-html action.")
            sys.exit(1)
        action_validate_html(args.file, args.memory_dir)

    elif args.action == "validate-ritual":
        if not args.ritual_type or not args.timestamp:
            print("❌ --ritual-type and --timestamp are required for validate-ritual action.")
            sys.exit(1)
        action_validate_ritual(args.ritual_type, args.timestamp, args.memory_dir)

    elif args.action == "health":
        action_health(args.memory_dir)


if __name__ == "__main__":
    main()
