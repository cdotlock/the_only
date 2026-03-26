#!/usr/bin/env python3
"""
The ONLY — Delivery Engine v2
Enhanced multi-channel delivery engine with narrative arc integration,
three-tier memory system, source pre-ranking, and knowledge archive.

Backward-compatible with v1 CLI. New actions: preview, archive, test.

Actions:
  deliver — Push each payload item as a separate message to all webhooks
            (with optional narrative arc reordering and memory tracking)
  status  — Print delivery + memory + archive status
  preview — Build narrative arc, show ritual plan without delivering
  archive — Search the knowledge archive
  test    — Run self-tests
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import urllib.request
from datetime import datetime

import orjson

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_v2 import MemoryManager
from narrative_arc import (
    NarrativeArc,
    CandidateItem,
    ArcPlan,
    format_preview,
    arc_from_json,
)
from source_graph import SourceGraph
from knowledge_archive import KnowledgeArchive, ArchiveEntry, generate_id
from optimized_io import load_json, save_json, timestamp

STATE_FILE = os.path.expanduser("~/memory/the_only_state.json")
CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")


def load_config() -> dict:
    """Load the main config file."""
    return load_json(CONFIG_FILE)


# ---------------------------------------------------------------------------
# Message formatting (duplicated from v1 — identical output)
# ---------------------------------------------------------------------------


def _html_escape(text: str) -> str:
    """Escape special HTML characters for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_item_message(item: dict, index: int, total: int, bot_name: str) -> str:
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
        return f"{header}\n{orjson.dumps(item).decode('utf-8')}"


def format_item_message_telegram(
    item: dict, index: int, total: int, bot_name: str
) -> str:
    """Telegram-specific format using HTML for clickable links."""
    header = f"<b>[{_html_escape(bot_name)}]</b> {index}/{total}"
    item_type = item.get("type", "unknown")

    if item_type == "interactive":
        title = _html_escape(item.get("title", "Untitled"))
        url = item.get("url", "")
        return f'{header}\n📰 <b>{title}</b>\n<a href="{url}">Read →</a>'

    elif item_type == "nanobanana":
        title = _html_escape(item.get("title", "Infographic"))
        return f"{header}\n🎨 <b>{title}</b>\n<i>Visual knowledge map via NanoBanana Pro</i>"

    elif item_type == "social_digest":
        return _html_escape(item.get("text", ""))

    else:
        return f"{header}\n{_html_escape(orjson.dumps(item).decode('utf-8'))}"


# ---------------------------------------------------------------------------
# Webhook push (duplicated from v1 — identical logic)
# ---------------------------------------------------------------------------


def push_message(
    platform: str, url: str, message: str, config: dict | None = None
) -> bool:
    """Send a single message to a webhook. Returns True on success."""
    try:
        req = urllib.request.Request(url, method="POST")
        req.add_header("Content-Type", "application/json")

        if platform == "discord":
            data = orjson.dumps({"content": message})
        elif platform == "telegram":
            chat_id = (config or {}).get("telegram_chat_id", "")
            if not chat_id:
                print("⚠️  Telegram: 'telegram_chat_id' not set in config. Skipping.")
                return False
            data = orjson.dumps(
                {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            )
        elif platform == "whatsapp":
            data = orjson.dumps({"body": message})
        elif platform == "feishu":
            data = orjson.dumps({"msg_type": "text", "content": {"text": message}})
        else:
            return False

        urllib.request.urlopen(req, data=data, timeout=10)
        return True
    except Exception as e:
        print(f"⚠️  Failed to push to {platform}: {e}")
        return False


# ---------------------------------------------------------------------------
# V2 helpers
# ---------------------------------------------------------------------------


def _payload_to_candidates(payload: list[dict]) -> list[CandidateItem]:
    """Convert delivery payload items to CandidateItem objects."""
    candidates: list[CandidateItem] = []
    for item in payload:
        candidates.append(
            CandidateItem(
                title=item.get("title", "Untitled"),
                url=item.get("url", ""),
                composite_score=item.get(
                    "composite_score", item.get("quality_score", 5.0)
                ),
                relevance_score=item.get("relevance_score", 5.0),
                depth_score=item.get("depth_score", 5.0),
                insight_density_score=item.get("insight_density_score", 5.0),
                uniqueness_score=item.get("uniqueness_score", 5.0),
                categories=item.get("categories", []),
                topics=item.get("topics", []),
                source=item.get("source", ""),
                is_serendipity=item.get("is_serendipity", False),
                is_echo=item.get("is_echo", False),
                curation_reason=item.get("curation_reason", item.get("why", "")),
            )
        )
    return candidates


def _update_archive_after_delivery(items: list[dict], arc_plan: ArcPlan | None) -> None:
    """After delivery, add entries to knowledge archive."""
    try:
        archive = KnowledgeArchive()
        now = datetime.now()
        ritual_id = now.strftime("%Y%m%d_%H%M")
        entries: list[ArchiveEntry] = []
        for i, item in enumerate(items):
            arc_pos = ""
            if arc_plan and i < len(arc_plan.items):
                arc_pos = arc_plan.items[i].position.value
            entry = ArchiveEntry(
                id=generate_id(now, i + 1),
                title=item.get("title", "Untitled"),
                topics=item.get("topics", []),
                quality_score=item.get("quality_score", 0.0),
                source=item.get("source", ""),
                arc_position=arc_pos,
                ritual_id=ritual_id,
                html_path=item.get("html_path", item.get("url", "")),
                delivered_at=now.isoformat(),
            )
            entries.append(entry)
        archive.append(entries)
        links = archive.auto_link(entries)
        if links:
            print(f"🔗 Created {links} cross-article links in archive.")
    except Exception as e:
        print(f"⚠️  Archive update failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def action_preflight(memory_dir: str = "~/memory") -> dict:
    """Load all memory tiers and config. Halt with message if core.json missing."""
    mm = MemoryManager(memory_dir)
    try:
        data = mm.load_all()
    except FileNotFoundError:
        print("❌ Core memory missing. Run initialization first.", file=sys.stderr)
        sys.exit(1)
    config = load_config()
    return {"memory": data, "config": config, "manager": mm}


def action_prerank(semantic_data: dict) -> list[tuple[str, float]]:
    """Pre-rank sources by expected yield using source intelligence."""
    si = semantic_data.get("source_intelligence", {})
    graph = SourceGraph(si)
    return graph.pre_rank()


def action_preview(payload_str: str) -> None:
    """Preview mode: show ritual plan with arc positions without delivering."""
    try:
        items = orjson.loads(payload_str)
    except orjson.JSONDecodeError:
        print("❌ Invalid JSON payload.", file=sys.stderr)
        sys.exit(1)
    candidates = _payload_to_candidates(items)
    arc = NarrativeArc(candidates)
    plan = arc.build()
    print(format_preview(plan))


def action_deliver(
    payload_str: str, dry_run: bool = False, memory_dir: str = "~/memory"
) -> None:
    """Enhanced delivery with narrative arc reordering and memory tracking.

    1. Parse payload JSON
    2. Try to load memory (non-fatal if missing — fall back to v1 behavior)
    3. If memory loaded: build narrative arc, reorder items by arc position
    4. For each item: format message, send to webhooks (EXACT same logic as v1)
    5. Save delivery state
    6. If memory loaded: save episodic entry with delivery stats
    7. If memory loaded: update archive with delivered articles
    8. Print summary
    """
    config = load_config()
    bot_name = config.get("name", "Ruby")
    max_items = config.get("items_per_ritual", 5)

    try:
        items = orjson.loads(payload_str)
    except orjson.JSONDecodeError:
        print("❌ Invalid JSON payload.")
        sys.exit(1)

    if len(items) > max_items:
        items = items[:max_items]

    # --- V2: Try loading memory (non-fatal) ---
    mm: MemoryManager | None = None
    memory_data: dict | None = None
    arc_plan: ArcPlan | None = None
    try:
        mm = MemoryManager(memory_dir)
        memory_data = mm.load_all()
    except Exception:
        mm = None
        memory_data = None

    # --- V2: Build narrative arc if memory available ---
    if memory_data is not None and items:
        try:
            candidates = _payload_to_candidates(items)
            arc = NarrativeArc(candidates, items_per_ritual=max_items)
            arc_plan = arc.build()
            # Reorder items to match arc positions
            if arc_plan and arc_plan.items:
                reordered: list[dict] = []
                for arc_item in arc_plan.items:
                    # Find original item by title match
                    for orig in items:
                        if orig.get("title", "Untitled") == arc_item.candidate.title:
                            reordered.append(orig)
                            break
                if len(reordered) == len(items):
                    items = reordered
        except Exception as e:
            print(f"⚠️  Arc building failed, using original order: {e}", file=sys.stderr)
            arc_plan = None

    total = len(items)
    delivery_results: list[dict] = []

    # --- Delivery loop (identical to v1) ---
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
                print(
                    "   Add webhook URLs to ~/memory/the_only_config.json under 'webhooks'."
                )
            else:
                print("⚠️  All webhook deliveries failed. Check your webhook URLs.")

    # --- V2: Save episodic entry ---
    if mm is not None and memory_data is not None:
        try:
            avg_quality = 0.0
            quality_scores = [
                item.get("quality_score", item.get("composite_score", 0.0))
                for item in items
            ]
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
            episodic_entry = {
                "ritual_id": datetime.now().strftime("%Y%m%d_%H%M"),
                "timestamp": datetime.now().isoformat(),
                "items_delivered": total,
                "avg_quality_score": round(avg_quality, 2),
                "arc_theme": arc_plan.theme if arc_plan else "",
                "dry_run": dry_run,
            }
            mm.save_episodic_entry(episodic_entry)
        except Exception as e:
            print(f"⚠️  Episodic save failed: {e}", file=sys.stderr)

    # --- V2: Update knowledge archive ---
    if memory_data is not None and not dry_run:
        _update_archive_after_delivery(items, arc_plan)

    print(f"\n✅ Engine processed {total} items.")


def action_archive(query: str, topics: str | None = None) -> None:
    """Search the knowledge archive."""
    archive = KnowledgeArchive()
    topic_list = [t.strip() for t in topics.split(",")] if topics else None
    results = archive.search(query=query, topics=topic_list)
    if not results:
        print("No articles found.")
        return
    print(f"📚 Found {len(results)} article(s):\n")
    for entry in results[:20]:
        score_str = f" ({entry.quality_score:.1f})" if entry.quality_score else ""
        topics_str = ", ".join(entry.topics[:5]) if entry.topics else ""
        print(f"  [{entry.id}] {entry.title}{score_str}")
        if topics_str:
            print(f"      Topics: {topics_str}")
        if entry.arc_position:
            print(f"      Arc: {entry.arc_position}")
        print()


def action_status() -> None:
    """Print delivery status summary with v2 memory and archive info."""
    # --- V1 status output (exactly replicated) ---
    config = load_config()
    state = load_json(STATE_FILE)

    bot_name = config.get("name", "Ruby")
    frequency = config.get("frequency", "daily")

    active_webhooks: list[str] = []
    if "webhooks" in config:
        for platform, url in config["webhooks"].items():
            if url:
                active_webhooks.append(platform)

    print(f"=== {bot_name} — Status ===")
    print(f"Frequency: {frequency}")
    print(f"Items per ritual: {config.get('items_per_ritual', 5)}")
    print(
        f"Active webhooks: {', '.join(active_webhooks) if active_webhooks else 'None configured'}"
    )

    if state:
        print(f"Last delivery: {state.get('last_delivery', 'Never')}")
        print(f"Items delivered: {state.get('items_delivered', 0)}")
    else:
        print("Last delivery: Never")

    # --- V2 additions ---
    try:
        mm = MemoryManager()
        data = mm.load_all()
        print(f"\n--- Memory System ---")
        ep = data.get("episodic", {})
        print(f"Episodic entries: {len(ep.get('entries', []))}")
        sem = data.get("semantic", {})
        print(f"Sources tracked: {len(sem.get('source_intelligence', {}))}")
        print(f"Last compressed: {sem.get('last_compressed', 'Never')}")
        core = data.get("core", {})
        focus = core.get("identity", {}).get("current_focus", [])
        if focus:
            print(f"User focus: {', '.join(focus)}")
    except Exception:
        print("\n--- Memory System ---")
        print("Not initialized (run initialization first)")

    try:
        archive = KnowledgeArchive()
        print(f"\n--- Knowledge Archive ---")
        print(f"Total articles: {archive.total_count()}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------


def _run_tests() -> None:
    """Run self-tests using tempfile, verifying all v2 integrations."""
    passed = 0
    failed = 0

    def _assert(condition: bool, name: str) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}", file=sys.stderr)

    print("🧪 Engine v2 — self-tests\n")

    # Test 1: _payload_to_candidates
    print("── Test: _payload_to_candidates ──")
    payload = [
        {
            "title": "Test Article",
            "url": "https://example.com",
            "composite_score": 8.5,
            "relevance_score": 7.0,
            "depth_score": 9.0,
            "insight_density_score": 6.5,
            "uniqueness_score": 8.0,
            "categories": ["ai", "ml"],
            "topics": ["transformers", "llm"],
            "source": "arxiv",
            "is_serendipity": True,
            "curation_reason": "Groundbreaking",
        },
        {"title": "Minimal Item"},
    ]
    candidates = _payload_to_candidates(payload)
    _assert(len(candidates) == 2, "two candidates created")
    _assert(candidates[0].title == "Test Article", "title preserved")
    _assert(candidates[0].composite_score == 8.5, "composite_score preserved")
    _assert(candidates[0].is_serendipity is True, "is_serendipity preserved")
    _assert(
        candidates[0].curation_reason == "Groundbreaking", "curation_reason preserved"
    )
    _assert(candidates[1].title == "Minimal Item", "minimal item title")
    _assert(
        candidates[1].composite_score == 5.0,
        "default composite_score from quality_score fallback",
    )
    _assert(candidates[1].relevance_score == 5.0, "default relevance_score")
    print()

    # Test 2: preview output
    print("── Test: preview output ──")
    preview_payload = [
        {
            "title": "Article A",
            "composite_score": 8.0,
            "topics": ["ai"],
            "categories": ["tech"],
            "curation_reason": "High quality",
        },
        {
            "title": "Article B",
            "composite_score": 7.0,
            "topics": ["ml"],
            "categories": ["science"],
            "is_serendipity": True,
        },
        {
            "title": "Article C",
            "composite_score": 6.0,
            "topics": ["ai", "ml"],
            "categories": ["tech"],
            "depth_score": 9.0,
            "insight_density_score": 9.0,
        },
    ]
    cands = _payload_to_candidates(preview_payload)
    arc = NarrativeArc(cands)
    plan = arc.build()
    preview_text = format_preview(plan)
    _assert("📋 Ritual Preview" in preview_text, "preview contains header")
    _assert("Arc:" in preview_text, "preview contains arc theme")
    _assert(len(plan.items) == 3, "3 items in arc plan")
    print()

    # Test 3: archive search with temp dir
    print("── Test: archive search ──")
    with tempfile.TemporaryDirectory(prefix="engine_v2_test_") as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        now = datetime.now()
        entries = [
            ArchiveEntry(
                id=generate_id(now, 1),
                title="AI Deep Dive",
                topics=["ai", "transformers"],
                quality_score=8.5,
                source="arxiv",
                ritual_id=now.strftime("%Y%m%d_%H%M"),
                delivered_at=now.isoformat(),
            ),
            ArchiveEntry(
                id=generate_id(now, 2),
                title="Rust Performance",
                topics=["rust", "systems"],
                quality_score=7.0,
                source="blog",
                ritual_id=now.strftime("%Y%m%d_%H%M"),
                delivered_at=now.isoformat(),
            ),
        ]
        archive.append(entries)
        _assert(archive.total_count() == 2, "archive has 2 entries")

        results = archive.search(query="ai")
        _assert(len(results) == 1, "search 'ai' returns 1 result")
        _assert(results[0].title == "AI Deep Dive", "correct article matched")

        results_topic = archive.search(topics=["rust"])
        _assert(len(results_topic) == 1, "topic search returns 1 result")

        links = archive.auto_link(entries)
        _assert(isinstance(links, int), "auto_link returns int")
    print()

    # Test 4: backward-compatible deliver dry-run
    print("── Test: deliver dry-run (v1 compat) ──")
    with tempfile.TemporaryDirectory(prefix="engine_v2_deliver_") as tmpdir:
        # Set up minimal config and state paths
        config_path = os.path.join(tmpdir, "the_only_config.json")
        state_path = os.path.join(tmpdir, "the_only_state.json")
        save_json(config_path, {"name": "TestBot", "items_per_ritual": 5})

        global CONFIG_FILE, STATE_FILE
        orig_config = CONFIG_FILE
        orig_state = STATE_FILE
        CONFIG_FILE = config_path
        STATE_FILE = state_path
        try:
            v1_payload = orjson.dumps(
                [
                    {
                        "type": "interactive",
                        "title": "Hello World",
                        "url": "https://example.com",
                    },
                    {"type": "nanobanana", "title": "Knowledge Map"},
                ]
            ).decode("utf-8")
            action_deliver(v1_payload, dry_run=True, memory_dir=tmpdir)
            state = load_json(state_path)
            _assert(
                state.get("items_delivered") == 2, "state records 2 items delivered"
            )
            _assert(len(state.get("results", [])) == 2, "state has 2 result entries")
            _assert(
                state["results"][0]["status"] == "dry_run", "dry_run status recorded"
            )
        finally:
            CONFIG_FILE = orig_config
            STATE_FILE = orig_state
    print()

    # Test 5: status doesn't crash when memory doesn't exist
    print("── Test: status with no memory ──")
    try:
        # action_status reads from default paths; if memory files don't exist,
        # it should print defaults without crashing
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            action_status()
        output = buf.getvalue()
        _assert("Status ===" in output, "status header printed")
        _assert("Frequency:" in output, "frequency line printed")
    except Exception as e:
        _assert(False, f"status crashed: {e}")
    print()

    # Test 6: format_item_message v1 compatibility
    print("── Test: format_item_message v1 compat ──")
    item_interactive = {
        "type": "interactive",
        "title": "My Article",
        "url": "https://x.com",
    }
    msg = format_item_message(item_interactive, 1, 3, "Ruby")
    _assert("[Ruby] 1/3" in msg, "header format correct")
    _assert("📰 My Article" in msg, "title with emoji")
    _assert("🔗 https://x.com" in msg, "url with emoji")

    item_nano = {"type": "nanobanana", "title": "Infographic X"}
    msg_nano = format_item_message(item_nano, 2, 3, "Ruby")
    _assert("🎨 Infographic X" in msg_nano, "nanobanana format")

    msg_tg = format_item_message_telegram(item_interactive, 1, 3, "Ruby")
    _assert("<b>[Ruby]</b>" in msg_tg, "telegram bold header")
    _assert('href="https://x.com"' in msg_tg, "telegram clickable link")
    print()

    # Test 7: _html_escape
    print("── Test: _html_escape ──")
    _assert(_html_escape("a & b") == "a &amp; b", "ampersand escaped")
    _assert(_html_escape("<script>") == "&lt;script&gt;", "angle brackets escaped")
    _assert(_html_escape("normal") == "normal", "no-op on clean text")
    print()

    # Test 8: action_prerank
    print("── Test: action_prerank ──")
    semantic = {
        "source_intelligence": {
            "arxiv": {"quality_avg": 9.0, "reliability": 1.0, "freshness": "daily"},
            "blog": {"quality_avg": 5.0, "reliability": 0.8, "freshness": "weekly"},
        }
    }
    ranked = action_prerank(semantic)
    _assert(len(ranked) >= 2, "at least 2 sources ranked")
    _assert(ranked[0][0] == "arxiv", "arxiv ranked first")
    _assert(ranked[0][1] > ranked[1][1], "arxiv yield > blog yield")

    empty_ranked = action_prerank({})
    _assert(empty_ranked == [], "empty source_intelligence → empty ranking")
    print()

    # Summary
    total = passed + failed
    print(f"\n🧪 Results: {passed}/{total} passed")
    if failed:
        print(f"❌ {failed} test(s) failed", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ All tests passed")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point — backward-compatible with v1 plus new actions."""
    parser = argparse.ArgumentParser(
        description="The ONLY — Delivery Engine v2 (Multi-channel + Arc + Memory)"
    )
    parser.add_argument(
        "--action",
        choices=["deliver", "status", "preview", "archive", "test"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--payload", type=str, help="JSON string of items (for deliver/preview)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print messages without sending to webhooks",
    )
    parser.add_argument("--query", type=str, help="Search query (for archive action)")
    parser.add_argument(
        "--topics", type=str, help="Comma-separated topics (for archive action)"
    )
    parser.add_argument(
        "--memory-dir",
        type=str,
        default="~/memory",
        help="Memory directory path",
    )

    args = parser.parse_args()

    if args.action == "deliver":
        if not args.payload:
            print("❌ --payload is required for deliver action.")
            sys.exit(1)
        action_deliver(args.payload, dry_run=args.dry_run, memory_dir=args.memory_dir)

    elif args.action == "status":
        action_status()

    elif args.action == "preview":
        if not args.payload:
            print("❌ --payload is required for preview action.")
            sys.exit(1)
        action_preview(args.payload)

    elif args.action == "archive":
        if not args.query and not args.topics:
            print("❌ --query or --topics is required for archive action.")
            sys.exit(1)
        action_archive(query=args.query or "", topics=args.topics)

    elif args.action == "test":
        _run_tests()


if __name__ == "__main__":
    main()
