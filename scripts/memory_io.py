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


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="memory_io — CLI for the-only v2 three-tier memory system"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["read", "write", "validate", "project", "status", "append-episodic"],
    )
    parser.add_argument("--tier", choices=["core", "semantic", "episodic"])
    parser.add_argument("--data", help="JSON string for write / append-episodic")
    parser.add_argument(
        "--memory-dir",
        default=os.path.expanduser("~/memory"),
        help="Memory directory (default: ~/memory)",
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


if __name__ == "__main__":
    main()
