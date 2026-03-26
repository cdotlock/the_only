#!/usr/bin/env python3
"""
Migrate V1 → V2 — One-Click Migration for the_only Memory Files
────────────────────────────────────────────────────────────────
Parses legacy V1 markdown/JSONL memory files and maps them to the
three-tier V2 JSON architecture (core, semantic, episodic).

Usage:
  python3 scripts/migrate_v1_to_v2.py [--dry-run] [--memory-dir ~/memory]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

# V2 default schemas (self-contained — no external dependency)
DEFAULT_CORE = {
    "version": "2.0",
    "name": "Ruby",
    "slogan": "In a world of increasing entropy, be the one who reduces it.",
    "deep_interests": [],
    "values": [],
    "reading_style": {},
    "updated_at": "",
}

DEFAULT_SEMANTIC = {
    "version": "2.0",
    "source_intelligence": {},
    "engagement_patterns": {},
    "emerging_interests": [],
    "style_preferences": {},
    "evolution_log": [],
    "last_maintenance": "",
}

DEFAULT_EPISODIC = {
    "version": "2.0",
    "entries": [],
    "last_compressed": "",
}


def save_json(path: str, data: dict | list) -> None:
    """Atomically write JSON to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


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
# CLI
# ══════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate V1 → V2 — One-Click Migration for the_only Memory Files"
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
    report = migrate(args.memory_dir, dry_run=args.dry_run)
    print(format_report(report))


if __name__ == "__main__":
    main()
