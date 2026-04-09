#!/usr/bin/env python3
"""
memory_io.py — Minimal CLI for the-only v2 three-tier JSON memory system.
───────────────────────────────────────────────────────────────────────────
Stdlib only.  No orjson, no pydantic, no external deps.

Tiers:
  core      the_only_core.json      — Stable identity
  semantic  the_only_semantic.json   — Cross-ritual patterns
  episodic  the_only_episodic.json   — Per-ritual buffer (50 FIFO)

Actions:
  read              Read one tier (prints JSON to stdout)
  write             Merge-write data into one tier
  validate          Validate all tiers, auto-repair missing keys
  project           Regenerate markdown projections from JSON tiers
  status            Print summary of all three tiers
  append-episodic   Append one entry to episodic buffer (FIFO 50)
  maintain          Run Maintenance Cycle: compress Episodic → Semantic, adjust ratios
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Default schemas ──────────────────────────────────────────────────────

DEFAULTS: dict[str, dict] = {
    "core": {
        "version": "2.0",
        "name": "Ruby",
        "slogan": "In a world of increasing entropy, be the one who reduces it.",
        "deep_interests": [],
        "values": [],
        "reading_style": {},
        "updated_at": "",
    },
    "semantic": {
        "version": "2.0",
        "source_intelligence": {},
        "engagement_patterns": {},
        "emerging_interests": [],
        "style_preferences": {},
        "evolution_log": [],
        "last_maintenance": "",
    },
    "episodic": {
        "version": "2.0",
        "entries": [],
        "last_compressed": "",
    },
}

FILENAMES: dict[str, str] = {
    "core": "the_only_core.json",
    "semantic": "the_only_semantic.json",
    "episodic": "the_only_episodic.json",
}

EPISODIC_CAP = 50

# ── Helpers ──────────────────────────────────────────────────────────────


def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tier_path(memory_dir: Path, tier: str) -> Path:
    return memory_dir / FILENAMES[tier]


def _load_tier(memory_dir: Path, tier: str) -> dict:
    """Load a tier from disk, returning defaults if missing or corrupt."""
    path = _tier_path(memory_dir, tier)
    if not path.exists():
        return json.loads(json.dumps(DEFAULTS[tier]))  # deep copy via JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _warn(f"{path}: {exc}; returning default schema")
        return json.loads(json.dumps(DEFAULTS[tier]))


def _save_tier(memory_dir: Path, tier: str, data: dict) -> None:
    memory_dir.mkdir(parents=True, exist_ok=True)
    path = _tier_path(memory_dir, tier)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base.  Lists and scalars are replaced."""
    merged = dict(base)
    for key, val in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


# ── Actions ──────────────────────────────────────────────────────────────


def action_read(memory_dir: Path, tier: str) -> None:
    data = _load_tier(memory_dir, tier)
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    print()


def action_write(memory_dir: Path, tier: str, raw_data: str) -> None:
    try:
        overlay = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(overlay, dict):
        print("error: --data must be a JSON object", file=sys.stderr)
        sys.exit(1)
    existing = _load_tier(memory_dir, tier)
    merged = _deep_merge(existing, overlay)
    if tier == "episodic":
        entries = merged.get("entries", [])
        if len(entries) > EPISODIC_CAP:
            merged["entries"] = entries[-EPISODIC_CAP:]
            _warn(f"episodic trimmed to {EPISODIC_CAP} entries (FIFO)")
    _save_tier(memory_dir, tier, merged)
    print(f"ok: {tier} written to {_tier_path(memory_dir, tier)}")


def action_validate(memory_dir: Path) -> None:
    issues = 0
    for tier in DEFAULTS:
        data = _load_tier(memory_dir, tier)
        default = DEFAULTS[tier]
        # Check version
        if "version" not in data:
            _warn(f"{tier}: missing 'version', adding default")
            data["version"] = default["version"]
            issues += 1
        # Check required top-level keys
        for key in default:
            if key not in data:
                _warn(f"{tier}: missing key '{key}', adding default")
                data[key] = json.loads(json.dumps(default[key]))
                issues += 1
        # Episodic cap
        if tier == "episodic":
            entries = data.get("entries", [])
            if len(entries) > EPISODIC_CAP:
                data["entries"] = entries[-EPISODIC_CAP:]
                _warn(f"{tier}: trimmed entries to {EPISODIC_CAP}")
                issues += 1
        _save_tier(memory_dir, tier, data)
    if issues == 0:
        print("validate: all tiers OK")
    else:
        print(f"validate: repaired {issues} issue(s)")


def action_status(memory_dir: Path) -> None:
    for tier in DEFAULTS:
        path = _tier_path(memory_dir, tier)
        data = _load_tier(memory_dir, tier)
        size = path.stat().st_size if path.exists() else 0
        mtime = (
            datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            if path.exists()
            else "n/a"
        )
        top_keys = len([k for k in data if k != "version"])
        extra = ""
        if tier == "episodic":
            n = len(data.get("entries", []))
            extra = f"  entries={n}/{EPISODIC_CAP}"
        print(f"{tier:10s}  {size:>7,} bytes  modified={mtime}  keys={top_keys}{extra}")


def action_append_episodic(memory_dir: Path, raw_data: str) -> None:
    try:
        entry = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(entry, dict):
        print("error: --data must be a JSON object", file=sys.stderr)
        sys.exit(1)
    data = _load_tier(memory_dir, "episodic")
    entries = data.get("entries", [])
    entries.append(entry)
    if len(entries) > EPISODIC_CAP:
        entries = entries[-EPISODIC_CAP:]
        _warn(f"episodic buffer at cap; oldest entry evicted")
    data["entries"] = entries
    _save_tier(memory_dir, "episodic", data)
    print(f"ok: episodic now has {len(entries)} entries")


def action_project(memory_dir: Path) -> None:
    core = _load_tier(memory_dir, "core")
    semantic = _load_tier(memory_dir, "semantic")

    # ── the_only_context.md ──
    src_intel = semantic.get("source_intelligence", {})
    src_lines = []
    for name, info in src_intel.items():
        if isinstance(info, dict):
            score = info.get("quality_score", "?")
            src_lines.append(f"- **{name}**: quality={score}")
        else:
            src_lines.append(f"- **{name}**: {info}")
    sources_block = "\n".join(src_lines) if src_lines else "_No source intelligence yet._"

    interests = ", ".join(core.get("deep_interests", [])) or "_none_"
    values = ", ".join(core.get("values", [])) or "_none_"

    context_md = f"""\
# the_only — Context Projection
> Auto-generated by memory_io.py at {_now_iso()}

## Identity
- **Name**: {core.get("name", "?")}
- **Slogan**: {core.get("slogan", "")}

## Cognitive State
- **Deep interests**: {interests}
- **Values**: {values}
- **Reading style**: {json.dumps(core.get("reading_style", {}), ensure_ascii=False)}

## Source Intelligence
{sources_block}

## Engagement Patterns
{json.dumps(semantic.get("engagement_patterns", {}), indent=2, ensure_ascii=False)}
"""

    context_path = memory_dir / "the_only_context.md"
    context_path.write_text(context_md, encoding="utf-8")

    # ── the_only_meta.md ──
    emerging = semantic.get("emerging_interests", [])
    emerging_block = "\n".join(f"- {e}" for e in emerging) if emerging else "_none_"

    evo_log = semantic.get("evolution_log", [])
    evo_block = ""
    for entry in evo_log[-10:]:  # last 10
        if isinstance(entry, dict):
            evo_block += f"- [{entry.get('date', '?')}] {entry.get('note', '')}\n"
        else:
            evo_block += f"- {entry}\n"
    evo_block = evo_block.strip() or "_No evolution log entries._"

    meta_md = f"""\
# the_only — Meta Projection
> Auto-generated by memory_io.py at {_now_iso()}

## Synthesis Style
{json.dumps(semantic.get("style_preferences", {}), indent=2, ensure_ascii=False)}

## Emerging Interests
{emerging_block}

## Evolution Log (last 10)
{evo_block}

## Last Maintenance
{semantic.get("last_maintenance", "never")}
"""

    meta_path = memory_dir / "the_only_meta.md"
    meta_path.write_text(meta_md, encoding="utf-8")

    print(f"ok: projected {context_path}")
    print(f"ok: projected {meta_path}")


def _avg_engagement(entry: dict) -> float:
    """Compute average engagement score for an episodic entry."""
    engagement = entry.get("engagement", {})
    if not engagement:
        return 0.0
    scores = [
        sig.get("score", 0)
        for sig in engagement.values()
        if isinstance(sig, dict)
    ]
    return sum(scores) / len(scores) if scores else 0.0


def _diagnose_low_engagement(
    entries: list[dict], semantic: dict
) -> dict:
    """Diagnose cause of consecutive low engagement."""
    recent = entries[-5:] if len(entries) >= 5 else entries
    older = entries[:-5] if len(entries) > 5 else []

    # Check if sources degraded
    src_intel = semantic.get("source_intelligence", {})
    low_reliability = [
        s for s, info in src_intel.items()
        if info.get("reliability", 1.0) < 0.5
    ]
    if len(low_reliability) >= 3:
        return {
            "cause": f"Source degradation — {len(low_reliability)} sources below 50% reliability",
            "action": "Replace low-reliability sources and diversify",
            "action_type": "source_refresh",
        }

    # Check if interest distribution shifted
    recent_cats: dict[str, int] = {}
    for e in recent:
        for cat, count in e.get("categories", {}).items():
            recent_cats[cat] = recent_cats.get(cat, 0) + count
    older_cats: dict[str, int] = {}
    for e in older:
        for cat, count in e.get("categories", {}).items():
            older_cats[cat] = older_cats.get(cat, 0) + count

    # If category distribution changed significantly
    if older_cats:
        old_top = max(older_cats, key=older_cats.get, default="")
        new_top = max(recent_cats, key=recent_cats.get, default="")
        if old_top != new_top:
            return {
                "cause": f"Interest shift detected — dominant category changed from '{old_top}' to '{new_top}'",
                "action": "Adjust ratios to match new interest pattern",
                "action_type": "ratio_shift",
            }

    # Default: unknown cause, diversify
    return {
        "cause": "Unknown — no clear source degradation or interest shift",
        "action": "Increase serendipity to 30%, diversify sources, wait for signal",
        "action_type": "diversify",
    }


def action_maintain(memory_dir: Path, force: bool = False) -> None:
    """Run a Maintenance Cycle: compress Episodic → Semantic, adjust ratios.

    Enforces a 24-hour cooldown between cycles to prevent double-processing.
    Use force=True to bypass the cooldown (e.g., manual invocation).
    """
    episodic = _load_tier(memory_dir, "episodic")
    semantic = _load_tier(memory_dir, "semantic")
    entries = episodic.get("entries", [])

    if not entries:
        print("maintain: no episodic entries to process")
        return

    # Cooldown: skip if last maintenance was < 24 hours ago
    if not force:
        last_maint = semantic.get("last_maintenance", "")
        if last_maint:
            try:
                last_dt = datetime.fromisoformat(last_maint.replace("Z", "+00:00"))
                hours_ago = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if hours_ago < 24:
                    print(
                        f"maintain: skipped — last maintenance was {hours_ago:.1f}h ago "
                        f"(cooldown: 24h). Use --force to override."
                    )
                    return
            except (ValueError, TypeError):
                pass  # corrupted timestamp, proceed anyway

    changes: list[str] = []

    # ── 1. Compute engagement averages by category ───────────────────────
    cat_scores: dict[str, list[float]] = {}
    source_scores: dict[str, list[float]] = {}
    source_failures: dict[str, int] = {}
    topic_mentions: dict[str, int] = {}

    for entry in entries:
        # Engagement by category
        cats = entry.get("categories", {})
        engagement = entry.get("engagement", {})
        for item_key, sig in engagement.items():
            if isinstance(sig, dict):
                score = sig.get("score", 0)
                topic = sig.get("topic", "")
                if topic:
                    topic_mentions[topic] = topic_mentions.get(topic, 0) + 1
                # Map to categories if available
                for cat in cats:
                    cat_scores.setdefault(cat, []).append(score)

        # Source tracking
        for src in entry.get("sources_used", []):
            source_scores.setdefault(src, []).append(
                entry.get("avg_quality_score", 5.0)
            )
        for src in entry.get("sources_failed", []):
            source_failures[src] = source_failures.get(src, 0) + 1

    # ── 2. Update engagement_patterns ────────────────────────────────────
    eng_patterns = semantic.get("engagement_patterns", {})
    for cat, scores in cat_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        old = eng_patterns.get(cat, {})
        old_count = old.get("count", 0)
        eng_patterns[cat] = {
            "avg": round(avg, 2),
            "count": old_count + len(scores),
            "trend": (
                "rising" if avg > old.get("avg", 0) + 0.3
                else "falling" if avg < old.get("avg", 0) - 0.3
                else "stable"
            ),
        }
    semantic["engagement_patterns"] = eng_patterns

    # ── 3. Update source_intelligence ────────────────────────────────────
    src_intel = semantic.get("source_intelligence", {})
    for src, scores in source_scores.items():
        avg_q = sum(scores) / len(scores) if scores else 0
        fails = source_failures.get(src, 0)
        total_attempts = len(scores) + fails
        reliability = len(scores) / total_attempts if total_attempts > 0 else 0
        existing = src_intel.get(src, {})
        src_intel[src] = {
            "quality_avg": round(avg_q, 1),
            "reliability": round(reliability, 2),
            "consecutive_failures": fails,
            "last_evaluated": _now_iso()[:10],
        }
        if existing:
            # Preserve fields not computed here
            for k in ("depth", "bias", "best_for", "redundancy_with"):
                if k in existing:
                    src_intel[src][k] = existing[k]
    semantic["source_intelligence"] = src_intel

    # ── 4. Detect emerging interests ─────────────────────────────────────
    emerging = semantic.get("emerging_interests", [])
    existing_topics = {e.get("topic", "").lower() for e in emerging}
    for topic, count in topic_mentions.items():
        if count >= 3 and topic.lower() not in existing_topics:
            emerging.append({
                "topic": topic,
                "signal_count": count,
                "first_seen": _now_iso()[:10],
                "status": "monitoring",
            })
            changes.append(f"New emerging interest: {topic} ({count} signals)")
    # Update signal counts and promote/fade existing
    for e in emerging:
        t = e.get("topic", "").lower()
        if t in {k.lower(): k for k in topic_mentions}:
            actual_key = next(k for k in topic_mentions if k.lower() == t)
            e["signal_count"] = e.get("signal_count", 0) + topic_mentions[actual_key]
            if e["signal_count"] >= 5 and e.get("status") == "monitoring":
                e["status"] = "confirmed"
                changes.append(f"Promoted to confirmed: {e['topic']}")
        elif e.get("status") != "faded":
            # No new signals
            e["status"] = "faded"
            changes.append(f"Faded: {e['topic']}")
    # Cap at 10
    emerging = [e for e in emerging if e.get("status") != "faded"][:10]
    semantic["emerging_interests"] = emerging

    # ── 5. Drift Detection ─────────────────────────────────────────────
    # Compare recent delivery categories against configured ratio.
    # If >60% from a single category, force redistribute.
    recent_cats: dict[str, int] = {}
    for entry in entries[-10:]:  # last 10 rituals
        for cat, count in entry.get("categories", {}).items():
            recent_cats[cat] = recent_cats.get(cat, 0) + count
    total_recent = sum(recent_cats.values())
    if total_recent > 0:
        for cat, count in recent_cats.items():
            pct = count / total_recent
            if pct > 0.60:
                changes.append(
                    f"Drift detected: {cat} at {pct:.0%} of recent deliveries (>60%)"
                )
                # Will be corrected in ratio adjustment below

    # ── 6. Source Vitality — auto-promote/demote ─────────────────────────
    for src, info in list(src_intel.items()):
        reliability = info.get("reliability", 1.0)
        quality_avg = info.get("quality_avg", 5.0)
        total_attempts = (
            len(source_scores.get(src, []))
            + source_failures.get(src, 0)
            + info.get("_historical_attempts", 0)
        )
        status = info.get("status", "active")

        # Auto-demote: reliability < 0.5 across 10+ attempts
        if reliability < 0.5 and total_attempts >= 10 and status != "demoted":
            info["status"] = "demoted"
            changes.append(
                f"Source demoted: {src} (reliability {reliability:.2f} across {total_attempts} attempts)"
            )

        # Auto-promote: quality_avg > 7 across 5+ items AND reliability > 0.8
        elif (
            quality_avg > 7.0
            and total_attempts >= 5
            and reliability > 0.8
            and status != "promoted"
        ):
            info["status"] = "promoted"
            changes.append(
                f"Source promoted: {src} (quality {quality_avg:.1f}, reliability {reliability:.2f})"
            )
    semantic["source_intelligence"] = src_intel

    # ── 7. Emergency Strategy Review ─────────────────────────────────────
    # Trigger: 3+ consecutive rituals with avg engagement < 1.0
    if len(entries) >= 3:
        recent_three = entries[-3:]
        consecutive_low = all(
            _avg_engagement(e) < 1.0 for e in recent_three
        )
        if consecutive_low:
            # Diagnose cause
            diag = _diagnose_low_engagement(entries, semantic)
            changes.append(f"EMERGENCY: 3+ consecutive low-engagement rituals")
            changes.append(f"  Diagnosis: {diag['cause']}")
            changes.append(f"  Action: {diag['action']}")

            # Apply emergency action
            if diag["action_type"] == "diversify":
                # Increase serendipity to 30%, diversify sources
                fetch = semantic.get("fetch_strategy", {})
                ratio = fetch.get("ratio", {})
                ratio["serendipity"] = 30
                fetch["ratio"] = ratio
                semantic["fetch_strategy"] = fetch
            elif diag["action_type"] == "source_refresh":
                # Mark bottom 3 sources for replacement
                sorted_sources = sorted(
                    src_intel.items(),
                    key=lambda x: x[1].get("quality_avg", 0),
                )
                for src_name, src_info in sorted_sources[:3]:
                    src_info["status"] = "needs_replacement"
                    changes.append(f"  Flagged for replacement: {src_name}")

            semantic["_emergency_alert_pending"] = True

    # ── 8. Adaptive ratio adjustment ─────────────────────────────────────
    fetch = semantic.get("fetch_strategy", {})
    ratio = fetch.get("ratio", {"tech": 50, "philosophy": 25, "serendipity": 15, "research": 10})
    for cat, data in eng_patterns.items():
        if cat in ratio:
            avg = data.get("avg", 0)
            if avg >= 3.0:
                boost = min(15, int((avg - 2.0) * 5))
                ratio[cat] = min(70, ratio[cat] + boost)
                changes.append(f"Ratio boost: {cat} +{boost}% (avg engagement {avg})")
            elif avg < 1.5 and data.get("count", 0) >= 10:
                reduce = min(15, int((1.5 - avg) * 10))
                ratio[cat] = max(5, ratio[cat] - reduce)
                changes.append(f"Ratio reduce: {cat} -{reduce}% (avg engagement {avg})")

    # Drift correction: if any category >60% in recent deliveries,
    # redistribute at least 10pp to other categories
    if total_recent > 0:
        for cat, count in recent_cats.items():
            pct = count / total_recent
            if pct > 0.60 and cat in ratio:
                excess = ratio[cat] - 40  # target: bring down to at most 40%
                if excess > 0:
                    ratio[cat] -= excess
                    # Distribute to other categories proportionally
                    others = [c for c in ratio if c != cat]
                    per_other = excess // max(len(others), 1)
                    for other in others:
                        ratio[other] = ratio.get(other, 0) + per_other
                    changes.append(
                        f"Drift correction: {cat} reduced by {excess}pp, redistributed"
                    )

    # Enforce serendipity floor
    if ratio.get("serendipity", 0) < 10:
        ratio["serendipity"] = 10
    # Normalize to 100
    total = sum(ratio.values())
    if total != 100 and total > 0:
        factor = 100.0 / total
        ratio = {k: max(1, round(v * factor)) for k, v in ratio.items()}
    fetch["ratio"] = ratio
    semantic["fetch_strategy"] = fetch

    # ── 9. Log changes ───────────────────────────────────────────────────
    evo_log = semantic.get("evolution_log", [])
    for change in changes:
        evo_log.append({"date": _now_iso()[:10], "note": change})
    # Cap at 20
    semantic["evolution_log"] = evo_log[-20:]
    semantic["last_maintenance"] = _now_iso()

    # ── 7. Compress Episodic (keep newest 25) ────────────────────────────
    if len(entries) > 25:
        episodic["entries"] = entries[-25:]
        episodic["last_compressed"] = _now_iso()
        _save_tier(memory_dir, "episodic", episodic)
        print(f"maintain: compressed episodic from {len(entries)} to 25 entries")
    else:
        print(f"maintain: episodic has {len(entries)} entries (no compression needed)")

    _save_tier(memory_dir, "semantic", semantic)

    # ── 8. Regenerate projections ────────────────────────────────────────
    action_project(memory_dir)

    print(f"maintain: {len(changes)} change(s) applied")
    for c in changes:
        print(f"  • {c}")


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="memory_io — CLI for the-only v2 three-tier memory system"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["read", "write", "validate", "project", "status", "append-episodic", "maintain"],
    )
    parser.add_argument("--tier", choices=["core", "semantic", "episodic"])
    parser.add_argument("--data", help="JSON string for write / append-episodic")
    parser.add_argument(
        "--memory-dir",
        default=os.path.expanduser("~/memory"),
        help="Memory directory (default: ~/memory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass maintenance cooldown (for maintain action)",
    )
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir)

    if args.action == "read":
        if not args.tier:
            parser.error("--tier required for read")
        action_read(memory_dir, args.tier)

    elif args.action == "write":
        if not args.tier:
            parser.error("--tier required for write")
        if not args.data:
            parser.error("--data required for write")
        action_write(memory_dir, args.tier, args.data)

    elif args.action == "validate":
        action_validate(memory_dir)

    elif args.action == "project":
        action_project(memory_dir)

    elif args.action == "status":
        action_status(memory_dir)

    elif args.action == "append-episodic":
        if not args.data:
            parser.error("--data required for append-episodic")
        action_append_episodic(memory_dir, args.data)

    elif args.action == "maintain":
        action_maintain(memory_dir, force=args.force)


if __name__ == "__main__":
    main()
