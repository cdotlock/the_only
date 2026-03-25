#!/usr/bin/env python3
"""
Migrate V1 → V2 — One-Click Migration for the_only Memory Files
────────────────────────────────────────────────────────────────
Parses legacy V1 markdown/JSONL memory files and maps them to the
three-tier V2 JSON architecture (core, semantic, episodic).

Actions:
  (default)  — Run migration (or dry-run with --dry-run)
  test       — Run self-tests with inline assertions using tempfile
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Ensure scripts/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_v2 import (
    DEFAULT_CORE,
    DEFAULT_EPISODIC,
    DEFAULT_SEMANTIC,
    CoreLayer,
    EpisodicLayer,
    SemanticLayer,
    save_json,
)


# ══════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════


@dataclass
class MigrationReport:
    """Report produced by the migration process."""

    migrated: list[str] = field(default_factory=list)
    inferred: list[str] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    backup_files: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# JSON I/O HELPERS
# ══════════════════════════════════════════════════════════════


def load_json(path: str, default: dict | list | None = None) -> dict | list:
    """Load JSON from path, returning default on missing/corrupt file."""
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️  {path} is not valid JSON: {e}", file=sys.stderr)
    return copy.deepcopy(default)


# ══════════════════════════════════════════════════════════════
# V1 PARSERS
# ══════════════════════════════════════════════════════════════


def _safe_json_parse(text: str, fallback: object = None) -> object:
    """Try to parse a JSON-like string, returning fallback on failure."""
    text = text.strip().strip("`").strip()
    # Handle backtick-quoted JSON: `["a","b"]`
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # Try replacing single quotes with double quotes
    try:
        return json.loads(text.replace("'", '"'))
    except (json.JSONDecodeError, ValueError):
        pass
    return fallback


def _split_sections(content: str) -> dict[str, str]:
    """Split markdown content by `## N.` section headers.

    Returns:
        Dict mapping section number (as str) to the section body text.
    """
    sections: dict[str, str] = {}
    pattern = re.compile(r"^##\s+(\d+)\.\s+", re.MULTILINE)
    matches = list(pattern.finditer(content))
    for i, m in enumerate(matches):
        num = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections[num] = content[start:end].strip()
    return sections


def parse_context_md(path: str) -> dict:
    """Parse V1 context.md into a structured dict.

    Args:
        path: Path to the_only_context.md (V1 format).

    Returns:
        Dict with keys: cognitive_state, fetch_strategy, engagement_tracker, evolution_log.
    """
    result: dict = {
        "cognitive_state": {},
        "fetch_strategy": {},
        "engagement_tracker": {},
        "evolution_log": [],
    }

    if not os.path.exists(path):
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"⚠️  Could not read {path}: {e}", file=sys.stderr)
        return result

    sections = _split_sections(content)

    # ── Section 1: Cognitive State ──
    sec1 = sections.get("1", "")
    if sec1:
        m = re.search(r"\*\*Current Focus\*\*:\s*(.+)", sec1)
        if m:
            raw = m.group(1).strip()
            # Could be a list or comma-separated
            parsed = _safe_json_parse(raw)
            if isinstance(parsed, list):
                result["cognitive_state"]["current_focus"] = [s.strip() for s in parsed]
            else:
                result["cognitive_state"]["current_focus"] = [
                    s.strip() for s in raw.split(",") if s.strip()
                ]

        m = re.search(r"\*\*Emotional Vibe\*\*:\s*(.+)", sec1)
        if m:
            result["cognitive_state"]["emotional_vibe"] = m.group(1).strip()

        m = re.search(r"\*\*Knowledge Gaps\*\*:\s*(.+)", sec1)
        if m:
            result["cognitive_state"]["knowledge_gaps"] = m.group(1).strip()

    # ── Section 2: Dynamic Fetch Strategy ──
    sec2 = sections.get("2", "")
    if sec2:
        m = re.search(r"\*\*Primary Sources\*\*:\s*`(.+?)`", sec2)
        if m:
            parsed = _safe_json_parse(m.group(1))
            if isinstance(parsed, list):
                result["fetch_strategy"]["primary_sources"] = parsed

        m = re.search(r"\*\*Exclusions\*\*:\s*`(.+?)`", sec2)
        if m:
            parsed = _safe_json_parse(m.group(1))
            if isinstance(parsed, list):
                result["fetch_strategy"]["exclusions"] = parsed

        m = re.search(r"\*\*Ratio\*\*:\s*`(.+?)`", sec2)
        if m:
            parsed = _safe_json_parse(m.group(1))
            if isinstance(parsed, dict):
                result["fetch_strategy"]["ratio"] = parsed

        m = re.search(r"\*\*Synthesis Rules\*\*:\s*(.+)", sec2)
        if m:
            raw = m.group(1).strip()
            parsed = _safe_json_parse(raw)
            if isinstance(parsed, list):
                result["fetch_strategy"]["synthesis_rules"] = parsed
            else:
                result["fetch_strategy"]["synthesis_rules"] = raw

        m = re.search(r"\*\*Tool Preferences\*\*:\s*`(.+?)`", sec2)
        if m:
            result["fetch_strategy"]["tool_preferences"] = m.group(1).strip()
        else:
            m = re.search(r"\*\*Tool Preferences\*\*:\s*(.+)", sec2)
            if m:
                val = m.group(1).strip().strip('"').strip("'")
                result["fetch_strategy"]["tool_preferences"] = val

        m = re.search(r"\*\*Source Health\*\*:\s*`(.+?)`", sec2)
        if m:
            parsed = _safe_json_parse(m.group(1))
            if isinstance(parsed, dict):
                result["fetch_strategy"]["source_health"] = parsed

    # ── Section 3: Engagement Tracker ──
    sec3 = sections.get("3", "")
    if sec3:
        tracker: dict[str, dict] = {}
        for m in re.finditer(
            r"^-\s+(\w[\w\s]*?):\s*([\d.]+)\s*\((\d+)\s*items?\)", sec3, re.MULTILINE
        ):
            category = m.group(1).strip().lower()
            avg = float(m.group(2))
            count = int(m.group(3))
            tracker[category] = {"avg": avg, "count": count}
        result["engagement_tracker"] = tracker

    # ── Section 4: The Ledger (skip — no direct V2 mapping) ──

    # ── Section 5: Evolution Log ──
    sec5 = sections.get("5", "")
    if sec5:
        evo_log: list[dict] = []
        for m in re.finditer(r"^-\s+\[(.+?)\]:\s*(.+)", sec5, re.MULTILINE):
            evo_log.append(
                {
                    "timestamp": m.group(1).strip(),
                    "description": m.group(2).strip(),
                }
            )
        result["evolution_log"] = evo_log

    return result


def parse_meta_md(path: str) -> dict:
    """Parse V1 meta.md into a structured dict.

    Args:
        path: Path to the_only_meta.md (V1 format).

    Returns:
        Dict with keys: synthesis_style, temporal_patterns, emerging_interests.
    """
    result: dict = {
        "synthesis_style": {},
        "temporal_patterns": {},
        "emerging_interests": [],
    }

    if not os.path.exists(path):
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"⚠️  Could not read {path}: {e}", file=sys.stderr)
        return result

    sections = _split_sections(content)

    # ── Section 1: Synthesis Style Insights ──
    sec1 = sections.get("1", "")
    if sec1:
        insights: dict[str, str] = {}
        for line in sec1.splitlines():
            line = line.strip()
            if line.startswith("-"):
                text = line.lstrip("- ").strip()
                if text:
                    # Use first significant word as key
                    key = re.sub(r"[^a-z0-9]+", "_", text[:40].lower()).strip("_")
                    insights[key] = text
        result["synthesis_style"] = insights

    # ── Section 2: Temporal Patterns ──
    sec2 = sections.get("2", "")
    if sec2:
        patterns: dict[str, str] = {}
        for line in sec2.splitlines():
            line = line.strip()
            if line.startswith("-"):
                text = line.lstrip("- ").strip()
                # Try to extract "Morning rituals: ..." → {"morning": "..."}
                m = re.match(r"(\w+)\s+rituals?:\s*(.+)", text, re.IGNORECASE)
                if m:
                    time_key = m.group(1).strip().lower()
                    patterns[time_key] = m.group(2).strip()
                elif text:
                    key = re.sub(r"[^a-z0-9]+", "_", text[:30].lower()).strip("_")
                    patterns[key] = text
        result["temporal_patterns"] = patterns

    # ── Section 3: Emerging Interests ──
    sec3 = sections.get("3", "")
    if sec3:
        interests: list[dict] = []
        for line in sec3.splitlines():
            line = line.strip()
            if line.startswith("-"):
                text = line.lstrip("- ").strip()
                if text:
                    # Try to extract signal count: "Category theory (mentioned 3 times, monitoring)"
                    m = re.match(
                        r"(.+?)\s*\((?:mentioned\s+)?(\d+)\s+times?,?\s*(\w+)?\)",
                        text,
                    )
                    if m:
                        interests.append(
                            {
                                "name": m.group(1).strip(),
                                "signal_count": int(m.group(2)),
                                "status": m.group(3).strip()
                                if m.group(3)
                                else "active",
                            }
                        )
                    else:
                        interests.append({"name": text, "status": "active"})
        result["emerging_interests"] = interests

    return result


def parse_ritual_log(path: str) -> dict:
    """Parse V1 ritual_log.jsonl into aggregated stats.

    Args:
        path: Path to the_only_ritual_log.jsonl (V1 format).

    Returns:
        Dict with keys: source_stats, ritual_count.
    """
    result: dict = {"source_stats": {}, "ritual_count": 0}

    if not os.path.exists(path):
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"⚠️  Could not read {path}: {e}", file=sys.stderr)
        return result

    ritual_count = 0
    source_stats: dict[str, dict] = {}

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"⚠️  ritual_log line {line_num} parse error: {e}", file=sys.stderr)
            continue

        ritual_count += 1
        avg_quality = entry.get("avg_quality", 0.0)
        sources_used = entry.get("sources_used", [])

        for src in sources_used:
            if src not in source_stats:
                source_stats[src] = {
                    "hits": 0,
                    "quality_sum": 0.0,
                    "quality_count": 0,
                }
            source_stats[src]["hits"] += 1
            if isinstance(avg_quality, (int, float)) and avg_quality > 0:
                source_stats[src]["quality_sum"] += avg_quality
                source_stats[src]["quality_count"] += 1

    # Compute averages
    for src, stats in source_stats.items():
        if stats["quality_count"] > 0:
            stats["quality_avg"] = round(
                stats["quality_sum"] / stats["quality_count"], 2
            )
        else:
            stats["quality_avg"] = 0.0
        # Clean up intermediate fields
        del stats["quality_sum"]
        del stats["quality_count"]

    result["source_stats"] = source_stats
    result["ritual_count"] = ritual_count
    return result


# ══════════════════════════════════════════════════════════════
# V1 → V2 MAPPERS
# ══════════════════════════════════════════════════════════════


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def map_to_core(parsed_context: dict) -> dict:
    """Map parsed V1 context data to V2 core.json structure.

    Args:
        parsed_context: Output of parse_context_md().

    Returns:
        Dict matching DEFAULT_CORE schema.
    """
    core = copy.deepcopy(DEFAULT_CORE)
    cog = parsed_context.get("cognitive_state", {})
    fs = parsed_context.get("fetch_strategy", {})
    now = _now_iso()

    # Identity
    core["identity"]["current_focus"] = cog.get("current_focus", [])
    core["identity"]["professional_domain"] = ""  # inferred — needs review
    core["identity"]["knowledge_level"] = {}
    core["identity"]["values"] = []
    core["identity"]["anti_interests"] = fs.get("exclusions", [])

    # Reading preferences — keep defaults, override emotional_vibe if present
    if cog.get("emotional_vibe"):
        core["reading_preferences"]["emotional_vibe"] = cog["emotional_vibe"]

    core["established_at"] = now
    core["last_validated"] = now

    return core


def map_to_semantic(
    parsed_context: dict,
    parsed_meta: dict,
    parsed_log: dict,
) -> dict:
    """Map parsed V1 data to V2 semantic.json structure.

    Args:
        parsed_context: Output of parse_context_md().
        parsed_meta: Output of parse_meta_md().
        parsed_log: Output of parse_ritual_log().

    Returns:
        Dict matching DEFAULT_SEMANTIC schema.
    """
    semantic = copy.deepcopy(DEFAULT_SEMANTIC)
    fs = parsed_context.get("fetch_strategy", {})
    now = _now_iso()

    semantic["last_compressed"] = now

    # Fetch strategy
    semantic["fetch_strategy"]["primary_sources"] = fs.get("primary_sources", [])
    semantic["fetch_strategy"]["exclusions"] = fs.get("exclusions", [])

    # Ratio — normalize keys to lowercase
    raw_ratio = fs.get("ratio", {})
    if isinstance(raw_ratio, dict):
        semantic["fetch_strategy"]["ratio"] = {
            k.lower(): v for k, v in raw_ratio.items()
        }

    # Synthesis rules — ensure list
    rules = fs.get("synthesis_rules", [])
    if isinstance(rules, str):
        rules = [rules] if rules else []
    semantic["fetch_strategy"]["synthesis_rules"] = rules

    semantic["fetch_strategy"]["tool_preferences"] = fs.get("tool_preferences", "")

    # Source intelligence — merge Source Health + ritual_log stats
    source_intel: dict = {}

    # From Source Health
    source_health = fs.get("source_health", {})
    for src, info in source_health.items():
        if isinstance(info, dict):
            source_intel[src] = {
                "quality_avg": info.get("quality_avg", 0.0),
                "hits": info.get("items_scored", info.get("hits", 0)),
                "consecutive_empty": info.get("consecutive_empty", 0),
            }

    # From ritual log source stats
    log_stats = parsed_log.get("source_stats", {})
    for src, stats in log_stats.items():
        if src in source_intel:
            # Merge — prefer Source Health quality, add hits
            source_intel[src]["hits"] += stats.get("hits", 0)
        else:
            source_intel[src] = {
                "quality_avg": stats.get("quality_avg", 0.0),
                "hits": stats.get("hits", 0),
                "consecutive_empty": 0,
            }

    semantic["source_intelligence"] = source_intel

    # Engagement patterns
    eng = parsed_context.get("engagement_tracker", {})
    engagement_patterns: dict = {}
    for category, data in eng.items():
        if isinstance(data, dict):
            engagement_patterns[category] = {
                "avg": data.get("avg", 0.0),
                "count": data.get("count", 0),
                "trend": "stable",
            }
    semantic["engagement_patterns"] = engagement_patterns

    # Temporal patterns (from meta.md)
    semantic["temporal_patterns"] = parsed_meta.get("temporal_patterns", {})

    # Synthesis effectiveness (from meta.md synthesis style)
    semantic["synthesis_effectiveness"] = parsed_meta.get("synthesis_style", {})

    # Emerging interests (from meta.md)
    semantic["emerging_interests"] = parsed_meta.get("emerging_interests", [])

    # Evolution log (from context.md)
    semantic["evolution_log"] = parsed_context.get("evolution_log", [])

    return semantic


# ══════════════════════════════════════════════════════════════
# BACKUP
# ══════════════════════════════════════════════════════════════


def backup_file(path: str) -> str:
    """Copy a file to path.v1.bak.

    Args:
        path: File path to back up.

    Returns:
        The backup file path.
    """
    backup_path = path + ".v1.bak"
    shutil.copy2(path, backup_path)
    return backup_path


# ══════════════════════════════════════════════════════════════
# MAIN MIGRATION
# ══════════════════════════════════════════════════════════════


def migrate(memory_dir: str, dry_run: bool = False) -> MigrationReport:
    """Run the full V1→V2 migration.

    Args:
        memory_dir: Path to memory directory (e.g. ~/memory).
        dry_run: If True, parse and map but do not write any files.

    Returns:
        MigrationReport detailing what was done.
    """
    expanded = os.path.expanduser(memory_dir)
    report = MigrationReport()

    # V1 file paths
    context_path = os.path.join(expanded, "the_only_context.md")
    meta_path = os.path.join(expanded, "the_only_meta.md")
    ritual_log_path = os.path.join(expanded, "the_only_ritual_log.jsonl")

    # V2 output paths
    core_path = os.path.join(expanded, "the_only_core.json")
    semantic_path = os.path.join(expanded, "the_only_semantic.json")
    episodic_path = os.path.join(expanded, "the_only_episodic.json")

    # ── Step 1: Check which V1 files exist ──
    v1_files = {
        "context.md": context_path,
        "meta.md": meta_path,
        "ritual_log.jsonl": ritual_log_path,
    }
    found_files: list[str] = []
    for label, fpath in v1_files.items():
        if os.path.exists(fpath):
            found_files.append(label)
        else:
            report.inferred.append(f"{label} not found — using defaults")

    if not found_files:
        report.needs_review.append("No V1 files found — all V2 files will use defaults")

    # ── Step 2: Backup existing V1 files ──
    if not dry_run:
        for label, fpath in v1_files.items():
            if os.path.exists(fpath):
                try:
                    bak = backup_file(fpath)
                    report.backup_files.append(bak)
                except OSError as e:
                    report.errors.append(f"Failed to backup {label}: {e}")

    # ── Step 3: Parse context.md ──
    parsed_context: dict = {
        "cognitive_state": {},
        "fetch_strategy": {},
        "engagement_tracker": {},
        "evolution_log": [],
    }
    if os.path.exists(context_path):
        try:
            parsed_context = parse_context_md(context_path)
            report.migrated.append("context.md parsed successfully")
        except Exception as e:
            report.errors.append(f"context.md parse error: {e}")

    # ── Step 4: Parse meta.md ──
    parsed_meta: dict = {
        "synthesis_style": {},
        "temporal_patterns": {},
        "emerging_interests": [],
    }
    if os.path.exists(meta_path):
        try:
            parsed_meta = parse_meta_md(meta_path)
            report.migrated.append("meta.md parsed successfully")
        except Exception as e:
            report.errors.append(f"meta.md parse error: {e}")

    # ── Step 5: Parse ritual_log.jsonl ──
    parsed_log: dict = {"source_stats": {}, "ritual_count": 0}
    if os.path.exists(ritual_log_path):
        try:
            parsed_log = parse_ritual_log(ritual_log_path)
            report.migrated.append(
                f"ritual_log.jsonl parsed ({parsed_log['ritual_count']} rituals)"
            )
        except Exception as e:
            report.errors.append(f"ritual_log.jsonl parse error: {e}")

    # ── Step 6: Map to V2 core.json ──
    try:
        core_data = map_to_core(parsed_context)
        report.migrated.append("core.json mapped")

        # Track inferred fields
        if not core_data["identity"]["current_focus"]:
            report.inferred.append("identity.current_focus — empty (no V1 data)")
        if not core_data["identity"]["professional_domain"]:
            report.inferred.append(
                "identity.professional_domain — empty (not in V1 format)"
            )
            report.needs_review.append(
                "Set identity.professional_domain manually in core.json"
            )
        report.inferred.append("identity.knowledge_level — empty (not in V1 format)")
        report.inferred.append("identity.values — empty (not in V1 format)")
        report.inferred.append(
            "reading_preferences.preferred_length — default 'long-form'"
        )
        report.inferred.append(
            "reading_preferences.preferred_style — default 'deep analysis'"
        )
    except Exception as e:
        report.errors.append(f"core.json mapping error: {e}")
        core_data = copy.deepcopy(DEFAULT_CORE)

    # ── Step 7: Map to V2 semantic.json ──
    try:
        semantic_data = map_to_semantic(parsed_context, parsed_meta, parsed_log)
        report.migrated.append("semantic.json mapped")
    except Exception as e:
        report.errors.append(f"semantic.json mapping error: {e}")
        semantic_data = copy.deepcopy(DEFAULT_SEMANTIC)

    # ── Step 8: Create empty episodic.json ──
    episodic_data = copy.deepcopy(DEFAULT_EPISODIC)
    report.inferred.append("episodic.json — empty (no V1 episodic data to migrate)")

    # ── Step 9: Write V2 files ──
    if not dry_run:
        os.makedirs(expanded, exist_ok=True)
        try:
            save_json(core_path, core_data)
            report.migrated.append(f"Wrote {core_path}")
        except OSError as e:
            report.errors.append(f"Failed to write core.json: {e}")

        try:
            save_json(semantic_path, semantic_data)
            report.migrated.append(f"Wrote {semantic_path}")
        except OSError as e:
            report.errors.append(f"Failed to write semantic.json: {e}")

        try:
            save_json(episodic_path, episodic_data)
            report.migrated.append(f"Wrote {episodic_path}")
        except OSError as e:
            report.errors.append(f"Failed to write episodic.json: {e}")
    else:
        report.inferred.append("Dry run — no files written")

    return report


# ══════════════════════════════════════════════════════════════
# REPORT FORMATTING
# ══════════════════════════════════════════════════════════════


def format_report(report: MigrationReport) -> str:
    """Format a MigrationReport as human-readable text.

    Args:
        report: The migration report to format.

    Returns:
        Multi-line string with emoji-prefixed sections.
    """
    lines: list[str] = []
    lines.append("═══════════════════════════════════════")
    lines.append("  V1 → V2 Migration Report")
    lines.append("═══════════════════════════════════════")
    lines.append("")

    if report.migrated:
        lines.append("✅ Migrated:")
        for item in report.migrated:
            lines.append(f"   • {item}")
        lines.append("")

    if report.inferred:
        lines.append("ℹ️  Inferred / Defaults:")
        for item in report.inferred:
            lines.append(f"   • {item}")
        lines.append("")

    if report.needs_review:
        lines.append("👀 Needs Review:")
        for item in report.needs_review:
            lines.append(f"   • {item}")
        lines.append("")

    if report.errors:
        lines.append("❌ Errors:")
        for item in report.errors:
            lines.append(f"   • {item}")
        lines.append("")

    if report.backup_files:
        lines.append("💾 Backups:")
        for item in report.backup_files:
            lines.append(f"   • {item}")
        lines.append("")

    # Summary line
    total_migrated = len(report.migrated)
    total_errors = len(report.errors)
    total_review = len(report.needs_review)
    if total_errors == 0:
        lines.append(
            f"🎉 Migration complete: {total_migrated} items migrated, "
            f"{total_review} need review"
        )
    else:
        lines.append(
            f"⚠️  Migration finished with {total_errors} error(s), "
            f"{total_migrated} items migrated, {total_review} need review"
        )

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# SELF-TESTS
# ══════════════════════════════════════════════════════════════

# Realistic V1 sample data for tests

SAMPLE_CONTEXT_MD = """\
# The Only — Context Map
*Last Compressed: 2026-03-20T09:00:00Z*

## 1. Cognitive State
- **Current Focus**: Learning Rust, Preparing for System Design Interviews
- **Emotional Vibe**: High stress / Curious
- **Knowledge Gaps**: Distributed consensus, Rust lifetime annotations

## 2. Dynamic Fetch Strategy
- **Primary Sources**: `["https://news.ycombinator.com", "r/MachineLearning"]`
- **Exclusions**: `["crypto", "celebrity gossip"]`
- **Synthesis Rules**: Condense AI papers, Always find one contrarian take
- **Ratio**: `{"Tech": 60, "Philosophy": 20, "Serendipity": 20}`
- **Tool Preferences**: `Use Tavily as primary search engine.`
- **Source Health**: `{"ycombinator": {"consecutive_empty": 0, "quality_avg": 6.5, "items_scored": 12}}`

## 3. Engagement Tracker
*Per-category average engagement scores.*
- Tech: 1.8 (15 items)
- Philosophy: 2.5 (6 items)

## 4. The Ledger
- [2026-03-19]: User loved the cross-domain article. [engagement: 2]

## 5. Evolution Log
- [2026-03-18]: Auto-shifted Ratio: Tech 60→50%. Reason: Philosophy avg engagement 2.5 vs Tech 1.2.
- [2026-03-15]: Added r/MachineLearning to Primary Sources.
"""

SAMPLE_META_MD = """\
# Ruby — Meta-Learning Notes
*Rituals completed: 42*

## 1. Synthesis Style Insights
- Deep analysis articles consistently get 2+ engagement
- News briefs are mostly skipped

## 2. Temporal Patterns
- Morning rituals: lower engagement
- Evening rituals: higher engagement

## 3. Emerging Interests
- Category theory (mentioned 3 times, monitoring)
- Rust async patterns (mentioned 5 times, active)

## 4. Self-Critique
- Sometimes too verbose in summaries

## 5. Behavioral Notes
- User prefers bullet points over paragraphs

## 6. Source Intelligence
- arxiv quality improving over last 10 rituals
"""

SAMPLE_RITUAL_LOG = """\
{"timestamp": "2026-03-20T09:00:00Z", "ritual_number": 42, "items_delivered": 5, "avg_quality": 7.2, "categories": {"tech": 3, "philosophy": 1, "serendipity": 1}, "sources_used": ["hn", "arxiv"]}
{"timestamp": "2026-03-19T09:00:00Z", "ritual_number": 41, "items_delivered": 4, "avg_quality": 6.8, "categories": {"tech": 2, "philosophy": 2}, "sources_used": ["hn", "reddit"]}
{"timestamp": "2026-03-18T09:00:00Z", "ritual_number": 40, "items_delivered": 6, "avg_quality": 8.1, "categories": {"tech": 4, "serendipity": 2}, "sources_used": ["arxiv", "hn"]}
"""


def action_test() -> None:
    """Run self-tests with inline assertions using tempfile."""
    passed = 0
    failed = 0

    def _assert(condition: bool, name: str) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    with tempfile.TemporaryDirectory(prefix="migrate_v1v2_test_") as tmpdir:
        print("🧪 Running migration self-tests...")
        print(f"   temp dir: {tmpdir}")
        print()

        # Write sample V1 files
        ctx_path = os.path.join(tmpdir, "the_only_context.md")
        meta_path = os.path.join(tmpdir, "the_only_meta.md")
        log_path = os.path.join(tmpdir, "the_only_ritual_log.jsonl")

        with open(ctx_path, "w") as f:
            f.write(SAMPLE_CONTEXT_MD)
        with open(meta_path, "w") as f:
            f.write(SAMPLE_META_MD)
        with open(log_path, "w") as f:
            f.write(SAMPLE_RITUAL_LOG)

        # ── Test 1: parse_context_md ──
        print("── parse_context_md ──")
        pc = parse_context_md(ctx_path)
        _assert(
            pc["cognitive_state"]["current_focus"]
            == [
                "Learning Rust",
                "Preparing for System Design Interviews",
            ],
            "current_focus parsed as list",
        )
        _assert(
            pc["cognitive_state"]["emotional_vibe"] == "High stress / Curious",
            "emotional_vibe parsed",
        )
        _assert(
            "https://news.ycombinator.com"
            in pc["fetch_strategy"].get("primary_sources", []),
            "primary_sources parsed",
        )
        _assert(
            "crypto" in pc["fetch_strategy"].get("exclusions", []),
            "exclusions parsed",
        )
        _assert(
            isinstance(pc["fetch_strategy"].get("ratio"), dict),
            "ratio parsed as dict",
        )
        _assert(
            pc["fetch_strategy"]["ratio"].get("Tech") == 60,
            "ratio Tech=60",
        )
        _assert(
            "ycombinator" in pc["fetch_strategy"].get("source_health", {}),
            "source_health parsed",
        )
        _assert(
            len(pc["engagement_tracker"]) == 2,
            "engagement_tracker has 2 categories",
        )
        _assert(
            pc["engagement_tracker"]["tech"]["avg"] == 1.8,
            "tech engagement avg=1.8",
        )
        _assert(
            pc["engagement_tracker"]["philosophy"]["count"] == 6,
            "philosophy engagement count=6",
        )
        _assert(len(pc["evolution_log"]) == 2, "evolution_log has 2 entries")
        _assert(
            "Auto-shifted" in pc["evolution_log"][0]["description"],
            "evolution_log entry content correct",
        )

        # ── Test 2: parse_meta_md ──
        print()
        print("── parse_meta_md ──")
        pm = parse_meta_md(meta_path)
        _assert(
            len(pm["synthesis_style"]) == 2,
            "synthesis_style has 2 insights",
        )
        _assert(
            "morning" in pm["temporal_patterns"],
            "temporal_patterns has morning key",
        )
        _assert(
            "evening" in pm["temporal_patterns"],
            "temporal_patterns has evening key",
        )
        _assert(
            len(pm["emerging_interests"]) == 2,
            "emerging_interests has 2 items",
        )
        _assert(
            pm["emerging_interests"][0]["name"] == "Category theory",
            "first interest is Category theory",
        )
        _assert(
            pm["emerging_interests"][0]["signal_count"] == 3,
            "Category theory signal_count=3",
        )
        _assert(
            pm["emerging_interests"][1]["status"] == "active",
            "Rust async patterns status=active",
        )

        # ── Test 3: parse_ritual_log ──
        print()
        print("── parse_ritual_log ──")
        pl = parse_ritual_log(log_path)
        _assert(pl["ritual_count"] == 3, "ritual_count=3")
        _assert("hn" in pl["source_stats"], "hn in source_stats")
        _assert("arxiv" in pl["source_stats"], "arxiv in source_stats")
        _assert(pl["source_stats"]["hn"]["hits"] == 3, "hn hits=3")
        _assert(pl["source_stats"]["arxiv"]["hits"] == 2, "arxiv hits=2")
        _assert(
            isinstance(pl["source_stats"]["hn"]["quality_avg"], float),
            "hn quality_avg is float",
        )

        # ── Test 4: map_to_core ──
        print()
        print("── map_to_core ──")
        core = map_to_core(pc)
        _assert(core["version"] == "2.0", "core version=2.0")
        _assert(
            core["identity"]["current_focus"]
            == [
                "Learning Rust",
                "Preparing for System Design Interviews",
            ],
            "core current_focus mapped",
        )
        _assert(
            core["identity"]["anti_interests"] == ["crypto", "celebrity gossip"],
            "core anti_interests from exclusions",
        )
        _assert(
            core["reading_preferences"]["emotional_vibe"] == "High stress / Curious",
            "core emotional_vibe mapped",
        )
        _assert(core["established_at"] != "", "core established_at set")
        _assert(core["last_validated"] != "", "core last_validated set")
        _assert(
            "preferred_length" in core["reading_preferences"],
            "reading_preferences has preferred_length",
        )

        # ── Test 5: map_to_semantic ──
        print()
        print("── map_to_semantic ──")
        sem = map_to_semantic(pc, pm, pl)
        _assert(sem["version"] == "2.0", "semantic version=2.0")
        _assert(
            "https://news.ycombinator.com" in sem["fetch_strategy"]["primary_sources"],
            "semantic primary_sources mapped",
        )
        _assert(
            "crypto" in sem["fetch_strategy"]["exclusions"],
            "semantic exclusions mapped",
        )
        # Check ratio keys are lowercase
        ratio_keys = list(sem["fetch_strategy"]["ratio"].keys())
        _assert(
            all(k == k.lower() for k in ratio_keys),
            "ratio keys are lowercase",
        )
        _assert(
            sem["fetch_strategy"]["ratio"]["tech"] == 60,
            "ratio tech=60 (lowercased)",
        )
        _assert(
            len(sem["source_intelligence"]) > 0,
            "source_intelligence populated",
        )
        _assert(
            "ycombinator" in sem["source_intelligence"],
            "ycombinator from Source Health",
        )
        _assert(
            "hn" in sem["source_intelligence"],
            "hn from ritual_log",
        )
        _assert(
            "tech" in sem["engagement_patterns"],
            "engagement_patterns has tech",
        )
        _assert(
            sem["engagement_patterns"]["tech"]["trend"] == "stable",
            "engagement trend=stable",
        )
        _assert(
            "morning" in sem["temporal_patterns"],
            "temporal_patterns from meta.md",
        )
        _assert(
            len(sem["synthesis_effectiveness"]) > 0,
            "synthesis_effectiveness from meta.md",
        )
        _assert(
            len(sem["emerging_interests"]) == 2,
            "emerging_interests from meta.md",
        )
        _assert(
            len(sem["evolution_log"]) == 2,
            "evolution_log from context.md",
        )

        # ── Test 6: dry_run doesn't create files ──
        print()
        print("── dry_run: no files written ──")
        dry_dir = os.path.join(tmpdir, "dry_test")
        os.makedirs(dry_dir)
        # Write V1 files into dry_dir
        with open(os.path.join(dry_dir, "the_only_context.md"), "w") as f:
            f.write(SAMPLE_CONTEXT_MD)
        report = migrate(dry_dir, dry_run=True)
        _assert(
            not os.path.exists(os.path.join(dry_dir, "the_only_core.json")),
            "core.json not created in dry run",
        )
        _assert(
            not os.path.exists(os.path.join(dry_dir, "the_only_semantic.json")),
            "semantic.json not created in dry run",
        )
        _assert(
            not os.path.exists(os.path.join(dry_dir, "the_only_episodic.json")),
            "episodic.json not created in dry run",
        )
        _assert(len(report.backup_files) == 0, "no backups in dry run")
        _assert(len(report.migrated) > 0, "dry run still reports parsed items")

        # ── Test 7: full migration creates all 3 JSON files ──
        print()
        print("── full migration: creates V2 files ──")
        full_dir = os.path.join(tmpdir, "full_test")
        os.makedirs(full_dir)
        with open(os.path.join(full_dir, "the_only_context.md"), "w") as f:
            f.write(SAMPLE_CONTEXT_MD)
        with open(os.path.join(full_dir, "the_only_meta.md"), "w") as f:
            f.write(SAMPLE_META_MD)
        with open(os.path.join(full_dir, "the_only_ritual_log.jsonl"), "w") as f:
            f.write(SAMPLE_RITUAL_LOG)

        report = migrate(full_dir, dry_run=False)

        core_out = os.path.join(full_dir, "the_only_core.json")
        sem_out = os.path.join(full_dir, "the_only_semantic.json")
        ep_out = os.path.join(full_dir, "the_only_episodic.json")

        _assert(os.path.exists(core_out), "core.json created")
        _assert(os.path.exists(sem_out), "semantic.json created")
        _assert(os.path.exists(ep_out), "episodic.json created")

        # Validate contents
        with open(core_out) as f:
            core_json = json.load(f)
        _assert(core_json["version"] == "2.0", "core.json version=2.0")
        _assert(
            "Learning Rust" in core_json["identity"]["current_focus"],
            "core.json has focus",
        )

        with open(sem_out) as f:
            sem_json = json.load(f)
        _assert(sem_json["version"] == "2.0", "semantic.json version=2.0")
        _assert(
            len(sem_json["fetch_strategy"]["primary_sources"]) == 2,
            "semantic.json has 2 sources",
        )

        with open(ep_out) as f:
            ep_json = json.load(f)
        _assert(ep_json["version"] == "2.0", "episodic.json version=2.0")
        _assert(ep_json["entries"] == [], "episodic.json entries empty")

        _assert(len(report.errors) == 0, f"no migration errors (got {report.errors})")

        # ── Test 8: backup files created ──
        print()
        print("── backup files ──")
        _assert(
            len(report.backup_files) == 3,
            f"3 backup files created (got {len(report.backup_files)})",
        )
        for bak in report.backup_files:
            _assert(os.path.exists(bak), f"backup exists: {os.path.basename(bak)}")
            _assert(bak.endswith(".v1.bak"), f"backup has .v1.bak suffix")

        # ── Test 9: missing V1 files don't crash ──
        print()
        print("── missing V1 files: graceful handling ──")
        empty_dir = os.path.join(tmpdir, "empty_test")
        os.makedirs(empty_dir)
        report = migrate(empty_dir, dry_run=False)
        _assert(len(report.errors) == 0, "no errors on empty dir")
        _assert(
            os.path.exists(os.path.join(empty_dir, "the_only_core.json")),
            "core.json created with defaults",
        )
        _assert(
            any("No V1 files" in item for item in report.needs_review),
            "report notes no V1 files found",
        )

        # ── Test 10: report formatting ──
        print()
        print("── format_report ──")
        report_text = format_report(report)
        _assert("Migration Report" in report_text, "report has title")
        _assert("✅" in report_text or "ℹ️" in report_text, "report has emoji sections")

    # Summary
    print()
    total = passed + failed
    print(f"{'=' * 40}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed > 0:
        print("❌ SOME TESTS FAILED", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ All tests passed")


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate V1 → V2 — One-Click Migration for the_only Memory Files"
    )
    parser.add_argument(
        "--action",
        choices=["migrate", "test"],
        default="migrate",
        help="Action to perform (default: migrate)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and map but do not write files",
    )
    parser.add_argument(
        "--memory-dir",
        default="~/memory",
        help="Memory directory (default: ~/memory)",
    )
    args = parser.parse_args()

    if args.action == "test":
        action_test()
    else:
        report = migrate(args.memory_dir, dry_run=args.dry_run)
        print(format_report(report))


if __name__ == "__main__":
    main()
