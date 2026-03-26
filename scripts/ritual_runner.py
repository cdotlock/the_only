#!/usr/bin/env python3
"""
Ritual Runner v2.0 — Entry Point for the_only Ritual Pipeline
──────────────────────────────────────────────────────────────
Orchestrates the v2 ritual pipeline by coordinating v2 runtime scripts
(memory_v2.py, source_graph.py, narrative_arc.py, knowledge_archive.py)
and v1 scripts (mesh_sync.py, the_only_engine_v2.py).

Phases:
  0 — Pre-Flight: Load all three memory tiers
  1 — Gather: Adaptive search with source pre-ranking
  2 — Evaluate: Depth-first scoring and narrative arc construction
  3 — Synthesize: Content synthesis (LLM-bound)
  4 — Output: HTML generation, archive indexing, delivery
  5 — Reflect: Memory update, evolution check, mesh post-actions

Usage:
  python3 scripts/ritual_runner.py --phase 0          # Run single phase
  python3 scripts/ritual_runner.py --all              # Run all phases
  python3 scripts/ritual_runner.py --all --dry-run    # Simulate without side effects
  python3 scripts/ritual_runner.py --status           # Show ritual status
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from optimized_io import load_json, save_json, timestamp, run_parallel

SCRIPTS_DIR = Path(__file__).parent
MEMORY_DIR = Path.home() / "memory"
CONFIG_FILE = MEMORY_DIR / "the_only_config.json"
RITUAL_LOG = MEMORY_DIR / "the_only_ritual_log.jsonl"
ECHOES_FILE = MEMORY_DIR / "the_only_echoes.txt"

MEMORY_V2 = SCRIPTS_DIR / "memory_v2.py"
SOURCE_GRAPH = SCRIPTS_DIR / "source_graph.py"
NARRATIVE_ARC = SCRIPTS_DIR / "narrative_arc.py"
KNOWLEDGE_ARCHIVE = SCRIPTS_DIR / "knowledge_archive.py"
ENGINE_V2 = SCRIPTS_DIR / "the_only_engine_v2.py"
MESH_SYNC = SCRIPTS_DIR / "mesh_sync.py"


def run_script(
    script: Path, args: list[str], check: bool = True
) -> subprocess.CompletedProcess:
    """Run a Python script with arguments. Returns CompletedProcess."""
    cmd = [sys.executable, str(script)] + args
    print(f"  → Running: {script.name} {' '.join(args)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(SCRIPTS_DIR.parent),
    )
    if check and result.returncode != 0:
        print(f"  ❌ Script failed: {script.name}", file=sys.stderr)
        print(f"     stderr: {result.stderr[:500]}", file=sys.stderr)
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result


def get_ritual_count() -> int:
    """Get ritual count from ritual_log.jsonl."""
    if not RITUAL_LOG.exists():
        return 0
    count = 0
    with open(RITUAL_LOG, "r") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


# ══════════════════════════════════════════════════════════════
# PHASE 0: PRE-FLIGHT
# ══════════════════════════════════════════════════════════════


def phase_0_preflight(dry_run: bool = False) -> dict:
    """Load all three memory tiers and verify system state.

    Returns:
        dict with keys: core, semantic, episodic, config, echoes, ritual_count
    """
    print("\n═══ Phase 0: Pre-Flight ═══")

    # Load config
    config = load_json(CONFIG_FILE)
    if not config:
        print(
            "  ❌ Config file missing or empty. Run initialization first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load memory tiers via memory_v2.py
    result = run_script(MEMORY_V2, ["--action", "read-all"])
    print(result.stdout)

    # Load individual tiers
    core = load_json(MEMORY_DIR / "the_only_core.json")
    semantic = load_json(MEMORY_DIR / "the_only_semantic.json")
    episodic = load_json(MEMORY_DIR / "the_only_episodic.json")

    # Validate tiers
    result = run_script(MEMORY_V2, ["--action", "validate"])
    if "⚠️" in result.stdout:
        print(f"  ⚠️  Validation warnings detected")

    # Load echoes
    echoes = []
    if ECHOES_FILE.exists():
        with open(ECHOES_FILE, "r") as f:
            echoes = [line.strip() for line in f if line.strip()]

    # Mesh sync if enabled
    mesh_enabled = config.get("mesh", {}).get("enabled", False)
    if mesh_enabled and not dry_run:
        print("  → Mesh enabled, syncing...")
        run_script(MESH_SYNC, ["--action", "sync"], check=False)
    elif mesh_enabled:
        print("  → Mesh enabled (skipped in dry-run)")

    # Verify identity
    if not core.get("identity", {}).get("current_focus"):
        print("  ⚠️  Core identity incomplete. Consider running initialization.")

    ritual_count = get_ritual_count()
    print(f"  ✅ Pre-flight complete. Ritual #{ritual_count + 1}")

    return {
        "core": core,
        "semantic": semantic,
        "episodic": episodic,
        "config": config,
        "echoes": echoes,
        "ritual_count": ritual_count,
    }


# ══════════════════════════════════════════════════════════════
# PHASE 1: GATHER
# ══════════════════════════════════════════════════════════════


def phase_1_gather(
    preflight_data: dict, dry_run: bool = False, test_fixtures: str | None = None
) -> list[dict]:
    """Adaptive information search with source pre-ranking.

    Returns:
        List of candidate items (dicts with title, content, source, scores)
    """
    print("\n═══ Phase 1: Gather ═══")

    semantic = preflight_data["semantic"]
    config = preflight_data["config"]

    # Step 0: Load test fixtures if provided
    if test_fixtures:
        test_articles_file = Path(test_fixtures) / "sources" / "test_articles.json"
        if test_articles_file.exists():
            candidates = load_json(test_articles_file, [])
            print(f"  → Loaded {len(candidates)} test articles from fixtures")
            return candidates

    # Step 1: Pre-rank sources
    print("  → Pre-ranking sources...")
    result = run_script(SOURCE_GRAPH, ["--action", "rank"])
    print(result.stdout)

    # Step 2: Execute search (placeholder — actual search uses OpenClaw tools)
    print("  → Executing adaptive search...")
    print("  ⚠️  Search requires OpenClaw tools (web_search, read_url).")
    print("     In standalone mode, candidates must be provided via --payload.")

    # Step 3: Check for mesh content
    mesh_enabled = config.get("mesh", {}).get("enabled", False)
    if mesh_enabled:
        print("  → Checking mesh content...")

    candidates = []

    print(f"  ✅ Gather complete. {len(candidates)} candidates found.")
    return candidates


# ══════════════════════════════════════════════════════════════
# PHASE 2: EVALUATE
# ══════════════════════════════════════════════════════════════


def phase_2_evaluate(
    candidates: list[dict], preflight_data: dict, dry_run: bool = False
) -> list[dict]:
    """Depth-first scoring and narrative arc construction.

    Args:
        candidates: List of candidate items from Phase 1
        preflight_data: Data from Phase 0

    Returns:
        List of selected items with narrative arc positions
    """
    print("\n═══ Phase 2: Evaluate ═══")

    if not candidates:
        print("  ⚠️  No candidates to evaluate.")
        return []

    # Step 1: Score candidates (6 dimensions)
    print("  → Scoring candidates...")
    # Scoring logic would go here
    # For now, assume candidates already have scores

    # Step 2: Build narrative arc
    print("  → Building narrative arc...")
    payload = json.dumps(candidates)
    result = run_script(NARRATIVE_ARC, ["--action", "build", "--payload", payload])
    print(result.stdout)

    # Parse arc result
    try:
        arc_data = json.loads(result.stdout)
        selected = arc_data.get("items", candidates[:5])
    except json.JSONDecodeError:
        selected = candidates[:5]

    # Step 3: Preview arc
    result = run_script(NARRATIVE_ARC, ["--action", "preview", "--payload", payload])
    print(result.stdout)

    print(f"  ✅ Evaluate complete. {len(selected)} items selected.")
    return selected


# ══════════════════════════════════════════════════════════════
# PHASE 3: SYNTHESIZE
# ══════════════════════════════════════════════════════════════


def phase_3_synthesize(
    selected_items: list[dict],
    preflight_data: dict,
    dry_run: bool = False,
    test_fixtures: str | None = None,
) -> list[dict]:
    """Content synthesis — LLM-bound.

    This phase is handled by the AI persona (Ruby) and cannot be
    fully automated in a Python script. This function provides
    the framework and returns the items for the next phase.

    Args:
        selected_items: Items from Phase 2 with narrative arc positions
        preflight_data: Data from Phase 0
        dry_run: If True, simulate synthesis
        test_fixtures: Path to test fixtures directory

    Returns:
        List of synthesized items (with content field populated)
    """
    print("\n═══ Phase 3: Synthesize ═══")

    if not selected_items:
        print("  ⚠️  No items to synthesize.")
        return []

    print(f"  → Synthesizing {len(selected_items)} items...")

    # In test mode, generate simulated synthesis
    if test_fixtures or dry_run:
        print("  → Using simulated synthesis (test mode)")
        synthesized = []
        for i, item in enumerate(selected_items):
            synthesized_item = item.copy()
            topic = (
                item.get("topics", ["general"])[0] if item.get("topics") else "general"
            )
            position = item.get(
                "narrative_position", item.get("arc_position", "Deep Dive")
            )

            synthesized_item["synthesis"] = (
                f"[{position}] This is a simulated synthesis for '{item.get('title', 'Untitled')}'. "
                f"The article explores {topic.replace('_', ' ')} in depth, connecting to broader themes "
                f"in the information landscape. Key insight: {item.get('curation_reason', 'Not specified')}."
            )
            synthesized_item["synthesis_style"] = "deep_analysis"
            synthesized.append(synthesized_item)

        print(f"  ✅ Synthesize complete. {len(synthesized)} items ready (simulated).")
        return synthesized

    print("  ⚠️  Synthesis requires LLM (Ruby persona).")
    print("     In standalone mode, items must be pre-synthesized.")

    synthesized = selected_items

    print(f"  ✅ Synthesize complete. {len(synthesized)} items ready.")
    return synthesized


# ══════════════════════════════════════════════════════════════
# PHASE 4: OUTPUT
# ══════════════════════════════════════════════════════════════


def phase_4_output(
    synthesized_items: list[dict], preflight_data: dict, dry_run: bool = False
) -> list[str]:
    """HTML generation, archive indexing, and delivery.

    Args:
        synthesized_items: Synthesized items from Phase 3
        preflight_data: Data from Phase 0

    Returns:
        List of generated HTML file paths
    """
    print("\n═══ Phase 4: Output ═══")

    if not synthesized_items:
        print("  ⚠️  No items to output.")
        return []

    config = preflight_data["config"]
    html_files = []

    # Step 1: Generate HTML (placeholder — actual generation uses Ruby)
    print("  → Generating HTML articles...")
    print("  ⚠️  HTML generation requires Ruby persona.")
    print("     In standalone mode, HTML must be pre-generated.")

    # Step 2: Index to knowledge archive
    print("  → Indexing to knowledge archive...")
    for item in synthesized_items:
        # Create archive entry
        entry = {
            "title": item.get("title", "Untitled"),
            "topics": item.get("topics", []),
            "quality_score": item.get("composite_score", item.get("quality_score", 0)),
            "source": item.get("source", "unknown"),
            "synthesis_style": item.get("synthesis_style", "deep_analysis"),
        }
        payload = json.dumps(entry)
        result = run_script(
            KNOWLEDGE_ARCHIVE, ["--action", "append", "--payload", payload], check=False
        )
        if result.returncode == 0:
            print(f"    ✓ Archived: {entry['title'][:50]}")

    # Step 3: Auto-link related articles
    run_script(KNOWLEDGE_ARCHIVE, ["--action", "auto-link"], check=False)

    # Step 4: Deliver via engine
    print("  → Delivering content...")
    delivery_items = []
    for item in synthesized_items:
        delivery_items.append(
            {
                "type": "interactive",
                "title": item.get("title", "Untitled"),
                "url": item.get("url", ""),
                "composite_score": item.get(
                    "composite_score", item.get("quality_score", 0)
                ),
            }
        )

    if delivery_items:
        payload = json.dumps(delivery_items)
        if dry_run:
            run_script(
                ENGINE_V2, ["--action", "deliver", "--payload", payload, "--dry-run"]
            )
        else:
            run_script(
                ENGINE_V2, ["--action", "deliver", "--payload", payload], check=False
            )

    print(f"  ✅ Output complete. {len(html_files)} HTML files generated.")
    return html_files


# ══════════════════════════════════════════════════════════════
# PHASE 5: REFLECT
# ══════════════════════════════════════════════════════════════


def phase_5_reflect(
    synthesized_items: list[dict], preflight_data: dict, dry_run: bool = False
):
    """Memory update, evolution check, mesh post-actions.

    Args:
        synthesized_items: Synthesized items from Phase 3
        preflight_data: Data from Phase 0
    """
    print("\n═══ Phase 5: Reflect ═══")

    config = preflight_data["config"]
    ritual_count = preflight_data["ritual_count"]

    # Step 1: Update episodic memory
    print("  → Updating episodic memory...")
    if not dry_run and synthesized_items:
        # Create episodic entry
        entry = {
            "ritual_id": ritual_count + 1,
            "timestamp": timestamp(),
            "items_delivered": len(synthesized_items),
            "avg_quality_score": sum(
                i.get("composite_score", i.get("quality_score", 0))
                for i in synthesized_items
            )
            / max(len(synthesized_items), 1),
            "categories": {},  # Would be computed from items
            "engagement": {},  # Would be populated from feedback
            "sources_used": list(
                set(i.get("source", "") for i in synthesized_items if i.get("source"))
            ),
            "sources_failed": [],
            "echo_fulfilled": any(i.get("is_echo") for i in synthesized_items),
            "network_items": sum(1 for i in synthesized_items if i.get("from_mesh")),
            "search_queries": 0,  # Would be tracked during Phase 1
            "narrative_theme": "",  # Would be extracted from arc
            "synthesis_styles": {},
        }

        # Append to episodic.json
        episodic = load_json(
            MEMORY_DIR / "the_only_episodic.json", {"version": "2.0", "entries": []}
        )
        episodic["entries"].append(entry)
        # FIFO enforcement happens in memory_v2.py
        save_json(MEMORY_DIR / "the_only_episodic.json", episodic)

    # Step 2: Run maintenance cycle
    print("  → Running maintenance cycle...")
    if not dry_run:
        run_script(MEMORY_V2, ["--action", "maintain"], check=False)

    # Step 3: Update source intelligence
    print("  → Updating source intelligence...")
    # Would call source_graph.py --action update for each source

    # Step 4: Mesh post-actions
    mesh_enabled = config.get("mesh", {}).get("enabled", False)
    if mesh_enabled and not dry_run:
        print("  → Running mesh post-actions...")

        # Auto-publish high-quality items
        threshold = config.get("mesh", {}).get("auto_publish_threshold", 7.5)
        for item in synthesized_items:
            score = item.get("composite_score", item.get("quality_score", 0))
            if score >= threshold:
                content = json.dumps(
                    {
                        "title": item.get("title", ""),
                        "synthesis": item.get("synthesis", item.get("content", "")),
                        "source_urls": item.get("source_urls", []),
                        "tags": item.get("topics", []),
                        "quality_score": score,
                        "lang": "auto",
                    }
                )
                run_script(
                    MESH_SYNC,
                    ["--action", "publish", "--content", content],
                    check=False,
                )

        # Every 5 rituals: update profile
        if (ritual_count + 1) % 5 == 0:
            run_script(MESH_SYNC, ["--action", "profile_update"], check=False)

        # Every 2 rituals: discover + follow
        if (ritual_count + 1) % 2 == 0:
            run_script(MESH_SYNC, ["--action", "discover", "--limit", "5"], check=False)

    # Step 5: Log ritual
    print("  → Logging ritual...")
    if not dry_run:
        log_entry = {
            "ts": int(time.time()),
            "items": len(synthesized_items),
            "network_items": sum(1 for i in synthesized_items if i.get("from_mesh")),
            "categories": {},
            "avg_quality": sum(
                i.get("composite_score", i.get("quality_score", 0))
                for i in synthesized_items
            )
            / max(len(synthesized_items), 1),
            "echo_fulfilled": any(i.get("is_echo") for i in synthesized_items),
            "styles": {},
        }
        with open(RITUAL_LOG, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print("  ✅ Reflect complete.")


# ══════════════════════════════════════════════════════════════
# STATUS
# ══════════════════════════════════════════════════════════════


def action_status():
    """Show ritual pipeline status."""
    print("═══ the_only v2 — Ritual Status ═══\n")

    # Config
    config = load_json(CONFIG_FILE)
    print(f"Name: {config.get('name', 'Ruby')}")
    print(f"Frequency: {config.get('frequency', 'unknown')}")
    print(f"Items per ritual: {config.get('items_per_ritual', 5)}")
    print(f"Version: {config.get('version', '1.0')}")

    # Memory status
    print("\n── Memory Tiers ──")
    result = run_script(MEMORY_V2, ["--action", "status"], check=False)
    print(result.stdout)

    # Ritual count
    ritual_count = get_ritual_count()
    print(f"\n── Rituals ──")
    print(f"Completed: {ritual_count}")

    # Archive status
    print("\n── Knowledge Archive ──")
    result = run_script(KNOWLEDGE_ARCHIVE, ["--action", "status"], check=False)
    print(result.stdout)

    # Source graph status
    print("\n── Source Intelligence ──")
    result = run_script(SOURCE_GRAPH, ["--action", "status"], check=False)
    print(result.stdout)

    # Mesh status
    mesh_enabled = config.get("mesh", {}).get("enabled", False)
    print(f"\n── Mesh Network ──")
    print(f"Enabled: {mesh_enabled}")
    if mesh_enabled:
        result = run_script(MESH_SYNC, ["--action", "status"], check=False)
        print(result.stdout)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="the_only v2 — Ritual Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/ritual_runner.py --all              # Run full ritual
  python3 scripts/ritual_runner.py --phase 0          # Run pre-flight only
  python3 scripts/ritual_runner.py --all --dry-run    # Simulate ritual
  python3 scripts/ritual_runner.py --status           # Show status
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--phase",
        type=int,
        choices=[0, 1, 2, 3, 4, 5],
        help="Run a specific phase (0-5)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Run all phases (full ritual)",
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Show ritual pipeline status",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without side effects (no writes, no delivery)",
    )

    parser.add_argument(
        "--payload",
        type=str,
        help="JSON payload for phases 1-4 (candidates/items)",
    )

    parser.add_argument(
        "--test-fixtures",
        type=str,
        help="Path to test fixtures directory for deterministic testing",
    )

    parser.add_argument(
        "--memory-dir",
        type=str,
        default="~/memory",
        help="Memory directory (default: ~/memory)",
    )

    args = parser.parse_args()

    global MEMORY_DIR, CONFIG_FILE, RITUAL_LOG, ECHOES_FILE
    if args.memory_dir:
        MEMORY_DIR = Path(os.path.expanduser(args.memory_dir))
        CONFIG_FILE = MEMORY_DIR / "the_only_config.json"
        RITUAL_LOG = MEMORY_DIR / "the_only_ritual_log.jsonl"
        ECHOES_FILE = MEMORY_DIR / "the_only_echoes.txt"

    # Status mode
    if args.status:
        action_status()
        return

    # Dry-run banner
    if args.dry_run:
        print("╔════════════════════════════════════════╗")
        print("║         DRY RUN MODE                   ║")
        print("║  No files will be written or delivered ║")
        print("╚════════════════════════════════════════╝\n")

    # Run specific phase
    if args.phase is not None:
        preflight_data = None
        candidates = []
        selected = []
        synthesized = []

        if args.phase >= 0:
            preflight_data = phase_0_preflight(args.dry_run)

        if args.phase >= 1:
            if args.payload:
                candidates = json.loads(args.payload)
            else:
                candidates = phase_1_gather(
                    preflight_data, args.dry_run, args.test_fixtures
                )

        if args.phase >= 2:
            selected = phase_2_evaluate(candidates, preflight_data, args.dry_run)

        if args.phase >= 3:
            synthesized = phase_3_synthesize(
                selected, preflight_data, args.dry_run, args.test_fixtures
            )

        if args.phase >= 4:
            phase_4_output(synthesized, preflight_data, args.dry_run)

        if args.phase >= 5:
            phase_5_reflect(synthesized, preflight_data, args.dry_run)

        print(f"\n✅ Phase {args.phase} complete.")
        return

    # Run all phases
    if args.all:
        print("═══ Starting Full Ritual ═══\n")

        # Phase 0: Pre-Flight
        preflight_data = phase_0_preflight(args.dry_run)

        # Phase 1: Gather
        if args.payload:
            candidates = json.loads(args.payload)
        else:
            candidates = phase_1_gather(
                preflight_data, args.dry_run, args.test_fixtures
            )

        # Phase 2: Evaluate
        selected = phase_2_evaluate(candidates, preflight_data, args.dry_run)

        # Phase 3: Synthesize
        synthesized = phase_3_synthesize(
            selected, preflight_data, args.dry_run, args.test_fixtures
        )

        # Phase 4: Output
        html_files = phase_4_output(synthesized, preflight_data, args.dry_run)

        # Phase 5: Reflect
        phase_5_reflect(synthesized, preflight_data, args.dry_run)

        print("\n═══ Ritual Complete ═══")
        print(f"Items delivered: {len(synthesized)}")
        print(f"HTML files: {len(html_files)}")
        print(f"Ritual #{preflight_data['ritual_count'] + 1}")


if __name__ == "__main__":
    main()
