#!/usr/bin/env python3
"""
Memory v2.0 — Three-Layer Memory System
────────────────────────────────────────
Implements the three-tier memory architecture for the_only:
  Core     — Stable identity, rarely changes
  Semantic — Cross-ritual patterns, updated every 5-15 rituals
  Episodic — Per-ritual impressions, rolling 50 FIFO

Actions:
  read-all  — Load and print all tiers summary
  validate  — Validate all tiers, report warnings
  maintain  — Run maintenance cycle
  project   — Generate markdown projections (context.md + meta.md)
  status    — Print tier stats (entry counts, last modified, etc.)
  test      — Run self-tests with inline assertions using tempfile
"""

from __future__ import annotations

import argparse
import copy
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone

import orjson

from optimized_io import (
    load_json,
    save_json,
    timestamp,
    CoreMemory,
    SemanticMemory,
    EpisodicMemory,
)

CORE_FILE = os.path.expanduser("~/memory/the_only_core.json")
SEMANTIC_FILE = os.path.expanduser("~/memory/the_only_semantic.json")
EPISODIC_FILE = os.path.expanduser("~/memory/the_only_episodic.json")
CONTEXT_MD = os.path.expanduser("~/memory/the_only_context.md")
META_MD = os.path.expanduser("~/memory/the_only_meta.md")

DEFAULT_CORE: dict = {
    "version": "2.0",
    "identity": {
        "current_focus": [],
        "professional_domain": "",
        "knowledge_level": {},
        "values": [],
        "anti_interests": [],
    },
    "reading_preferences": {
        "preferred_length": "long-form",
        "preferred_style": "deep analysis",
        "emotional_vibe": "intellectually curious",
    },
    "established_at": "",
    "last_validated": "",
}

DEFAULT_SEMANTIC: dict = {
    "version": "2.0",
    "last_compressed": "",
    "fetch_strategy": {
        "primary_sources": [],
        "exclusions": [],
        "ratio": {"tech": 50, "serendipity": 20, "research": 15, "philosophy": 15},
        "synthesis_rules": [],
        "tool_preferences": "",
    },
    "source_intelligence": {},
    "engagement_patterns": {},
    "temporal_patterns": {},
    "synthesis_effectiveness": {},
    "emerging_interests": [],
    "evolution_log": [],
}

DEFAULT_EPISODIC: dict = {
    "version": "2.0",
    "entries": [],
}

SIZE_LIMITS: dict[str, int] = {
    "evolution_log": 20,
    "source_intelligence": 30,
    "emerging_interests": 10,
    "entries": 50,
}


# ══════════════════════════════════════════════════════════════
# DEEP MERGE
# ══════════════════════════════════════════════════════════════


def _deep_merge(target: dict, defaults: dict) -> dict:
    """Recursively fill missing keys in target from defaults.

    Only adds keys that are absent. Existing values are never overwritten.
    Returns the mutated target for convenience.
    """
    for key, default_val in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(default_val)
        elif isinstance(default_val, dict) and isinstance(target[key], dict):
            _deep_merge(target[key], default_val)
    return target


# ══════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════


def validate_tier(
    data: dict,
    defaults: dict,
    size_limits: dict[str, int] | None = None,
) -> tuple[dict, list[str]]:
    """Validate a memory tier, repair missing keys, enforce size limits.

    Args:
        data: The tier data to validate.
        defaults: Default schema to merge missing keys from.
        size_limits: Optional mapping of key -> max length for list/dict trimming.

    Returns:
        Tuple of (repaired_data, warnings). Never silently drops data —
        all trimming is reported in warnings.
    """
    warnings: list[str] = []
    repaired = copy.deepcopy(data)

    # Check version field
    if "version" not in repaired:
        warnings.append("Missing 'version' field — set to default")
        repaired["version"] = defaults.get("version", "2.0")
    elif repaired["version"] != defaults.get("version", "2.0"):
        warnings.append(
            f"Version mismatch: found '{repaired['version']}', expected '{defaults.get('version', '2.0')}'"
        )

    # Deep merge missing keys from defaults
    before_keys = _count_keys(repaired)
    _deep_merge(repaired, defaults)
    after_keys = _count_keys(repaired)
    if after_keys > before_keys:
        warnings.append(
            f"Filled {after_keys - before_keys} missing key(s) from defaults"
        )

    # Enforce size limits
    if size_limits:
        for key, max_size in size_limits.items():
            _enforce_limit(repaired, key, max_size, warnings)

    return repaired, warnings


def _count_keys(d: dict, _depth: int = 0) -> int:
    """Count total keys in a nested dict."""
    count = 0
    for val in d.values():
        count += 1
        if isinstance(val, dict) and _depth < 10:
            count += _count_keys(val, _depth + 1)
    return count


def _enforce_limit(data: dict, key: str, max_size: int, warnings: list[str]) -> None:
    """Trim a list or dict field to max_size, appending warnings."""
    val = data.get(key)
    if val is None:
        return

    if isinstance(val, list) and len(val) > max_size:
        trimmed = len(val) - max_size
        data[key] = val[-max_size:]  # keep newest (trim oldest)
        warnings.append(
            f"Trimmed '{key}': removed {trimmed} oldest entries (limit {max_size})"
        )

    elif isinstance(val, dict) and len(val) > max_size:
        # For dicts (e.g. source_intelligence), trim by lowest quality_avg
        items = list(val.items())
        items.sort(key=lambda x: _extract_quality(x[1]), reverse=True)
        trimmed_count = len(items) - max_size
        data[key] = dict(items[:max_size])
        warnings.append(
            f"Trimmed '{key}': removed {trimmed_count} lowest-quality entries (limit {max_size})"
        )


def _extract_quality(val: object) -> float:
    """Extract quality_avg from a value, defaulting to 0.0."""
    if isinstance(val, dict):
        return float(val.get("quality_avg", 0.0))
    return 0.0


# ══════════════════════════════════════════════════════════════
# CORE LAYER
# ══════════════════════════════════════════════════════════════


class CoreLayer:
    """Manages the Core memory tier — stable identity, rarely changes."""

    def __init__(self, memory_dir: str = "~/memory") -> None:
        self._dir = os.path.expanduser(memory_dir)
        self._path = os.path.join(self._dir, "the_only_core.json")

    def read(self) -> dict:
        """Read core data, applying defaults for any missing fields."""
        data = load_json(self._path, copy.deepcopy(DEFAULT_CORE))
        repaired, warnings = validate_tier(data, DEFAULT_CORE)
        for w in warnings:
            print(f"⚠️  [core] {w}", file=sys.stderr)
        return repaired

    def write(self, data: dict) -> None:
        """Write core data to disk."""
        save_json(self._path, data)

    def update_identity(self, changes: dict) -> dict:
        """Merge changes into identity sub-object and persist.

        Args:
            changes: Dict of identity fields to update.

        Returns:
            The updated core data.
        """
        data = self.read()
        data["identity"].update(changes)
        data["last_validated"] = _now_iso()
        self.write(data)
        return data

    def update_reading_preferences(self, changes: dict) -> dict:
        """Merge changes into reading_preferences and persist.

        Args:
            changes: Dict of reading_preferences fields to update.

        Returns:
            The updated core data.
        """
        data = self.read()
        data["reading_preferences"].update(changes)
        data["last_validated"] = _now_iso()
        self.write(data)
        return data

    def touch_validated(self) -> dict:
        """Update last_validated timestamp and persist.

        Returns:
            The updated core data.
        """
        data = self.read()
        data["last_validated"] = _now_iso()
        self.write(data)
        return data


# ══════════════════════════════════════════════════════════════
# SEMANTIC LAYER
# ══════════════════════════════════════════════════════════════


class SemanticLayer:
    """Manages the Semantic memory tier — cross-ritual patterns."""

    def __init__(self, memory_dir: str = "~/memory") -> None:
        self._dir = os.path.expanduser(memory_dir)
        self._path = os.path.join(self._dir, "the_only_semantic.json")

    def read(self) -> dict:
        """Read semantic data, applying defaults for any missing fields."""
        data = load_json(self._path, copy.deepcopy(DEFAULT_SEMANTIC))
        repaired, warnings = validate_tier(
            data,
            DEFAULT_SEMANTIC,
            {
                "evolution_log": SIZE_LIMITS["evolution_log"],
                "source_intelligence": SIZE_LIMITS["source_intelligence"],
                "emerging_interests": SIZE_LIMITS["emerging_interests"],
            },
        )
        for w in warnings:
            print(f"⚠️  [semantic] {w}", file=sys.stderr)
        return repaired

    def write(self, data: dict) -> None:
        """Write semantic data to disk."""
        save_json(self._path, data)

    def update_fetch_strategy(self, changes: dict) -> dict:
        """Merge changes into fetch_strategy and persist.

        Args:
            changes: Dict of fetch_strategy fields to update.

        Returns:
            The updated semantic data.
        """
        data = self.read()
        data["fetch_strategy"].update(changes)
        data["last_compressed"] = _now_iso()
        self.write(data)
        return data

    def add_evolution_entry(self, entry: dict) -> dict:
        """Append an evolution entry, trimming oldest if over cap (20).

        Args:
            entry: The evolution log entry to add.

        Returns:
            The updated semantic data.
        """
        data = self.read()
        log = data.get("evolution_log", [])
        log.append(entry)
        if len(log) > SIZE_LIMITS["evolution_log"]:
            trimmed = len(log) - SIZE_LIMITS["evolution_log"]
            log = log[-SIZE_LIMITS["evolution_log"] :]
            print(
                f"⚠️  [semantic] evolution_log trimmed: {trimmed} oldest entries removed",
                file=sys.stderr,
            )
        data["evolution_log"] = log
        self.write(data)
        return data

    def update_source_intelligence(self, source_name: str, source_data: dict) -> dict:
        """Update source intelligence for a source, trimming by lowest quality_avg if over cap (30).

        Args:
            source_name: Name/key for the source.
            source_data: Intelligence data for this source.

        Returns:
            The updated semantic data.
        """
        data = self.read()
        si = data.get("source_intelligence", {})
        si[source_name] = source_data

        if len(si) > SIZE_LIMITS["source_intelligence"]:
            items = sorted(
                si.items(), key=lambda x: _extract_quality(x[1]), reverse=True
            )
            trimmed = len(items) - SIZE_LIMITS["source_intelligence"]
            si = dict(items[: SIZE_LIMITS["source_intelligence"]])
            print(
                f"⚠️  [semantic] source_intelligence trimmed: {trimmed} lowest-quality entries removed",
                file=sys.stderr,
            )
        data["source_intelligence"] = si
        self.write(data)
        return data

    def add_emerging_interest(self, interest: dict) -> dict:
        """Add an emerging interest, trimming faded first then oldest if over cap (10).

        Args:
            interest: The interest dict to add (may have 'status' field).

        Returns:
            The updated semantic data.
        """
        data = self.read()
        interests = data.get("emerging_interests", [])
        interests.append(interest)

        if len(interests) > SIZE_LIMITS["emerging_interests"]:
            # First remove "faded" entries
            faded = [i for i in interests if i.get("status") == "faded"]
            non_faded = [i for i in interests if i.get("status") != "faded"]

            if faded and len(non_faded) <= SIZE_LIMITS["emerging_interests"]:
                # Removing faded is enough
                removed = len(interests) - len(non_faded)
                interests = non_faded
                print(
                    f"⚠️  [semantic] emerging_interests trimmed: {removed} faded entries removed",
                    file=sys.stderr,
                )
            else:
                # Still over limit — trim oldest from non_faded after removing all faded
                removed_faded = len(faded)
                remaining = non_faded
                if len(remaining) > SIZE_LIMITS["emerging_interests"]:
                    trimmed = len(remaining) - SIZE_LIMITS["emerging_interests"]
                    remaining = remaining[-SIZE_LIMITS["emerging_interests"] :]
                    print(
                        f"⚠️  [semantic] emerging_interests trimmed: {removed_faded} faded + {trimmed} oldest entries removed",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"⚠️  [semantic] emerging_interests trimmed: {removed_faded} faded entries removed",
                        file=sys.stderr,
                    )
                interests = remaining

        data["emerging_interests"] = interests
        self.write(data)
        return data

    def get_source_intelligence(self) -> dict:
        """Return the source_intelligence dict.

        Returns:
            The source_intelligence mapping.
        """
        data = self.read()
        return data.get("source_intelligence", {})


# ══════════════════════════════════════════════════════════════
# EPISODIC LAYER
# ══════════════════════════════════════════════════════════════


class EpisodicLayer:
    """Manages the Episodic memory tier — per-ritual impressions, FIFO 50."""

    def __init__(self, memory_dir: str = "~/memory") -> None:
        self._dir = os.path.expanduser(memory_dir)
        self._path = os.path.join(self._dir, "the_only_episodic.json")

    def read(self) -> dict:
        """Read episodic data, applying defaults for any missing fields."""
        data = load_json(self._path, copy.deepcopy(DEFAULT_EPISODIC))
        repaired, warnings = validate_tier(
            data, DEFAULT_EPISODIC, {"entries": SIZE_LIMITS["entries"]}
        )
        for w in warnings:
            print(f"⚠️  [episodic] {w}", file=sys.stderr)
        return repaired

    def write(self, data: dict) -> None:
        """Write episodic data to disk."""
        save_json(self._path, data)

    def append_entry(self, entry: dict) -> dict:
        """Append an episodic entry, enforcing FIFO with cap of 50.

        Args:
            entry: The ritual entry to append.

        Returns:
            The updated episodic data.
        """
        data = self.read()
        entries = data.get("entries", [])
        entries.append(entry)
        if len(entries) > SIZE_LIMITS["entries"]:
            trimmed = len(entries) - SIZE_LIMITS["entries"]
            entries = entries[-SIZE_LIMITS["entries"] :]
            print(
                f"⚠️  [episodic] entries trimmed: {trimmed} oldest entries removed (FIFO {SIZE_LIMITS['entries']})",
                file=sys.stderr,
            )
        data["entries"] = entries
        self.write(data)
        return data

    def needs_compression(self) -> tuple[bool, str]:
        """Determine if episodic buffer needs compression into semantic.

        Rules:
          - buffer > 25 AND engagement variance > 1.0 → True (variance)
          - buffer > 50 → True (forced)
          - 3+ consecutive entries with avg_quality_score < 1.0 → True (emergency)

        Returns:
            Tuple of (should_compress, reason).
        """
        raw = load_json(self._path, copy.deepcopy(DEFAULT_EPISODIC))
        raw_entries = raw.get("entries", [])
        raw_count = len(raw_entries)

        if raw_count > 50:
            return True, f"forced: buffer size {raw_count} exceeds 50"

        data = self.read()
        entries = data.get("entries", [])
        count = len(entries)

        if count > 50:
            return True, f"forced: buffer size {count} exceeds 50"

        # Rule: 3+ consecutive low quality
        if count >= 3:
            consecutive_low = 0
            for entry in entries:
                score = entry.get("avg_quality_score", 5.0)
                if isinstance(score, (int, float)) and score < 1.0:
                    consecutive_low += 1
                    if consecutive_low >= 3:
                        return (
                            True,
                            "emergency: 3+ consecutive entries with avg_quality_score < 1.0",
                        )
                else:
                    consecutive_low = 0

        # Rule: buffer > 25 AND engagement variance > 1.0
        if count > 25:
            engagement_values = []
            for entry in entries:
                eng = entry.get("engagement")
                if isinstance(eng, (int, float)):
                    engagement_values.append(float(eng))
            if engagement_values and len(engagement_values) >= 2:
                variance = _variance(engagement_values)
                if variance > 1.0:
                    return (
                        True,
                        f"variance: buffer {count} > 25 with engagement variance {variance:.2f} > 1.0",
                    )

        return False, ""

    def get_recent(self, n: int) -> list[dict]:
        """Return the N most recent episodic entries.

        Args:
            n: Number of recent entries to return.

        Returns:
            List of the n most recent entries (or all if fewer exist).
        """
        data = self.read()
        entries = data.get("entries", [])
        return entries[-n:] if n < len(entries) else list(entries)


# ══════════════════════════════════════════════════════════════
# MEMORY MANAGER
# ══════════════════════════════════════════════════════════════


class MemoryManager:
    """Unified interface for the three-tier memory system.

    Coordinates reads, writes, validation, maintenance, and projection
    generation across Core, Semantic, and Episodic layers.
    """

    def __init__(self, memory_dir: str = "~/memory") -> None:
        self._dir = os.path.expanduser(memory_dir)
        self.core = CoreLayer(memory_dir)
        self.semantic = SemanticLayer(memory_dir)
        self.episodic = EpisodicLayer(memory_dir)

    def load_all(self) -> dict:
        """Read all three tiers, validate, and return combined dict.

        Returns:
            Dict with keys "core", "semantic", "episodic".
        """
        return {
            "core": self.core.read(),
            "semantic": self.semantic.read(),
            "episodic": self.episodic.read(),
        }

    def save_episodic_entry(self, entry: dict) -> None:
        """Append an episodic entry via the EpisodicLayer.

        Args:
            entry: The ritual entry to append.
        """
        self.episodic.append_entry(entry)

    def update_semantic(self, changes: dict) -> None:
        """Apply changes to the semantic layer.

        Delegates to specific update methods based on the keys in changes.
        Supported keys: fetch_strategy, source_intelligence, emerging_interests,
        evolution_log, and any other top-level semantic key.

        Args:
            changes: Dict of semantic fields to update.
        """
        data = self.semantic.read()
        for key, val in changes.items():
            if key == "fetch_strategy" and isinstance(val, dict):
                data["fetch_strategy"].update(val)
            elif key == "source_intelligence" and isinstance(val, dict):
                data["source_intelligence"].update(val)
                # Enforce size limit
                si = data["source_intelligence"]
                if len(si) > SIZE_LIMITS["source_intelligence"]:
                    items = sorted(
                        si.items(), key=lambda x: _extract_quality(x[1]), reverse=True
                    )
                    data["source_intelligence"] = dict(
                        items[: SIZE_LIMITS["source_intelligence"]]
                    )
            else:
                data[key] = val
        data["last_compressed"] = _now_iso()
        self.semantic.write(data)

    def update_core(self, changes: dict) -> None:
        """Apply changes to the core layer.

        Delegates to specific update methods based on the keys in changes.
        Supported keys: identity, reading_preferences, and any other top-level core key.

        Args:
            changes: Dict of core fields to update.
        """
        data = self.core.read()
        for key, val in changes.items():
            if key == "identity" and isinstance(val, dict):
                data["identity"].update(val)
            elif key == "reading_preferences" and isinstance(val, dict):
                data["reading_preferences"].update(val)
            else:
                data[key] = val
        data["last_validated"] = _now_iso()
        self.core.write(data)

    def run_maintenance(self) -> dict:
        """Run maintenance cycle: check compression, project markdowns.

        Returns:
            Report dict with keys: compression_needed, compression_reason,
            compressed, projections_written, warnings.
        """
        report: dict = {
            "compression_needed": False,
            "compression_reason": "",
            "compressed": False,
            "projections_written": False,
            "warnings": [],
        }

        # Load all tiers
        all_data = self.load_all()
        core = all_data["core"]
        semantic = all_data["semantic"]
        episodic = all_data["episodic"]

        # Check compression triggers
        needs, reason = self.episodic.needs_compression()
        report["compression_needed"] = needs
        report["compression_reason"] = reason

        if needs:
            print(f"🔄 Compression triggered: {reason}", file=sys.stderr)
            # Mark semantic as compressed
            semantic["last_compressed"] = _now_iso()
            self.semantic.write(semantic)
            report["compressed"] = True

        # Generate markdown projections
        write_projections(core, semantic, episodic, self._dir)
        report["projections_written"] = True

        return report

    def get_context_snapshot(self) -> dict:
        """Build a merged view useful for ritual pre-flight.

        Returns:
            Dict with core identity, reading preferences, fetch strategy,
            recent episodic entries, and compression status.
        """
        all_data = self.load_all()
        core = all_data["core"]
        semantic = all_data["semantic"]
        episodic = all_data["episodic"]

        needs, reason = self.episodic.needs_compression()

        return {
            "identity": core.get("identity", {}),
            "reading_preferences": core.get("reading_preferences", {}),
            "fetch_strategy": semantic.get("fetch_strategy", {}),
            "source_intelligence_count": len(semantic.get("source_intelligence", {})),
            "emerging_interests": semantic.get("emerging_interests", []),
            "recent_entries": episodic.get("entries", [])[-5:],
            "episodic_count": len(episodic.get("entries", [])),
            "compression_needed": needs,
            "compression_reason": reason,
        }


# ══════════════════════════════════════════════════════════════
# MARKDOWN PROJECTIONS
# ══════════════════════════════════════════════════════════════


def generate_context_md(core: dict, semantic: dict) -> str:
    """Generate the context.md markdown from core and semantic tiers.

    Args:
        core: The core tier data.
        semantic: The semantic tier data.

    Returns:
        Markdown string for context.md.
    """
    identity = core.get("identity", {})
    prefs = core.get("reading_preferences", {})
    fetch = semantic.get("fetch_strategy", {})
    si = semantic.get("source_intelligence", {})
    engagement = semantic.get("engagement_patterns", {})
    evo = semantic.get("evolution_log", [])
    timestamp = semantic.get("last_compressed", _now_iso())

    # Current focus
    focus_list = identity.get("current_focus", [])
    focus_str = ", ".join(focus_list) if focus_list else "(none)"

    # Emotional vibe
    vibe = prefs.get("emotional_vibe", "")

    # Knowledge level
    kl = identity.get("knowledge_level", {})
    kl_str = ", ".join(f"{k}: {v}" for k, v in kl.items()) if kl else "(none)"

    # Primary sources
    sources = fetch.get("primary_sources", [])
    sources_str = ", ".join(sources) if sources else "(none)"

    # Exclusions
    excl = fetch.get("exclusions", [])
    excl_str = ", ".join(excl) if excl else "(none)"

    # Synthesis rules
    rules = fetch.get("synthesis_rules", [])
    rules_str = "\n".join(f"  - {r}" for r in rules) if rules else "  - (none)"

    # Ratio
    ratio = fetch.get("ratio", {})
    ratio_str = ", ".join(f"{k}: {v}%" for k, v in ratio.items()) if ratio else "(none)"

    # Engagement patterns
    if engagement:
        eng_lines = []
        for k, v in engagement.items():
            eng_lines.append(f"- **{k}**: {v}")
        engagement_str = "\n".join(eng_lines)
    else:
        engagement_str = "- (no engagement data yet)"

    # Top 5 sources by quality_avg
    si_items = sorted(si.items(), key=lambda x: _extract_quality(x[1]), reverse=True)[
        :5
    ]
    if si_items:
        si_lines = []
        for name, info in si_items:
            quality = _extract_quality(info)
            detail = info if isinstance(info, dict) else {}
            hits = detail.get("hits", "?")
            si_lines.append(f"- **{name}**: quality_avg={quality:.1f}, hits={hits}")
        si_str = "\n".join(si_lines)
    else:
        si_str = "- (no source intelligence yet)"

    # Evolution log (last 10)
    recent_evo = evo[-10:]
    if recent_evo:
        evo_lines = []
        for entry in recent_evo:
            ts = entry.get("timestamp", "")
            desc = entry.get("description", entry.get("change", str(entry)))
            evo_lines.append(f"- [{ts}] {desc}")
        evo_str = "\n".join(evo_lines)
    else:
        evo_str = "- (no evolution log entries yet)"

    return f"""# The Only — Context Map
*Last Compressed: {timestamp}*
*Generated from: core.json + semantic.json*

## 1. Cognitive State
- **Current Focus**: {focus_str}
- **Emotional Vibe**: {vibe}
- **Knowledge Level**: {kl_str}

## 2. Dynamic Fetch Strategy
- **Primary Sources**: {sources_str}
- **Exclusions**: {excl_str}
- **Synthesis Rules**:
{rules_str}
- **Ratio**: {ratio_str}

## 3. Engagement Tracker
{engagement_str}

## 4. Source Intelligence (Top 5)
{si_str}

## 5. Evolution Log (Last 10)
{evo_str}
"""


def generate_meta_md(semantic: dict, episodic: dict) -> str:
    """Generate the meta.md markdown from semantic and episodic tiers.

    Args:
        semantic: The semantic tier data.
        episodic: The episodic tier data.

    Returns:
        Markdown string for meta.md.
    """
    timestamp = _now_iso()
    synth = semantic.get("synthesis_effectiveness", {})
    temporal = semantic.get("temporal_patterns", {})
    emerging = semantic.get("emerging_interests", [])
    entries = episodic.get("entries", [])

    # Synthesis style insights
    if synth:
        synth_lines = []
        for k, v in synth.items():
            synth_lines.append(f"- **{k}**: {v}")
        synth_str = "\n".join(synth_lines)
    else:
        synth_str = "- (no synthesis data yet)"

    # Temporal patterns
    if temporal:
        temp_lines = []
        for k, v in temporal.items():
            temp_lines.append(f"- **{k}**: {v}")
        temp_str = "\n".join(temp_lines)
    else:
        temp_str = "- (no temporal data yet)"

    # Emerging interests
    if emerging:
        ei_lines = []
        for interest in emerging:
            if isinstance(interest, dict):
                name = interest.get("name", interest.get("topic", str(interest)))
                status = interest.get("status", "active")
                ei_lines.append(f"- {name} (status: {status})")
            else:
                ei_lines.append(f"- {interest}")
        ei_str = "\n".join(ei_lines)
    else:
        ei_str = "- (no emerging interests yet)"

    # Recent self-notes (from last 10 episodic entries)
    recent = entries[-10:]
    notes = []
    for entry in recent:
        note = entry.get("self_notes", "")
        if note:
            rid = entry.get("ritual_id", "?")
            notes.append(f"- [{rid}] {note}")
    notes_str = "\n".join(notes) if notes else "- (no self-notes yet)"

    return f"""# Ruby — Meta-Learning Notes
*Last updated: {timestamp}*

## 1. Synthesis Style Insights
{synth_str}

## 2. Temporal Patterns
{temp_str}

## 3. Emerging Interests
{ei_str}

## 4. Recent Self-Notes
{notes_str}
"""


def write_projections(
    core: dict,
    semantic: dict,
    episodic: dict,
    memory_dir: str = "~/memory",
) -> None:
    """Write context.md and meta.md projection files.

    Args:
        core: The core tier data.
        semantic: The semantic tier data.
        episodic: The episodic tier data.
        memory_dir: Directory to write the markdown files into.
    """
    expanded = os.path.expanduser(memory_dir)

    ctx_path = os.path.join(expanded, "the_only_context.md")
    meta_path = os.path.join(expanded, "the_only_meta.md")

    ctx_md = generate_context_md(core, semantic)
    meta_md = generate_meta_md(semantic, episodic)

    os.makedirs(expanded, exist_ok=True)
    with open(ctx_path, "w", encoding="utf-8") as f:
        f.write(ctx_md)
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(meta_md)

    print(f"📝 Wrote {ctx_path}", file=sys.stderr)
    print(f"📝 Wrote {meta_path}", file=sys.stderr)


# ══════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════


def _now_iso() -> str:
    return timestamp()


def _variance(values: list[float]) -> float:
    """Compute population variance of a list of floats."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


# ══════════════════════════════════════════════════════════════
# CLI ACTIONS
# ══════════════════════════════════════════════════════════════


def action_read_all(memory_dir: str) -> None:
    """Load and print all tiers summary."""
    mm = MemoryManager(memory_dir)
    all_data = mm.load_all()

    print("═══ Core ═══")
    print(orjson.dumps(all_data["core"], option=orjson.OPT_INDENT_2).decode("utf-8"))
    print()
    print("═══ Semantic ═══")
    sem = all_data["semantic"]
    print(
        f"  fetch_strategy sources: {len(sem.get('fetch_strategy', {}).get('primary_sources', []))}"
    )
    print(f"  source_intelligence: {len(sem.get('source_intelligence', {}))} entries")
    print(f"  evolution_log: {len(sem.get('evolution_log', []))} entries")
    print(f"  emerging_interests: {len(sem.get('emerging_interests', []))} entries")
    print(f"  last_compressed: {sem.get('last_compressed', '(never)')}")
    print()
    print("═══ Episodic ═══")
    ep = all_data["episodic"]
    entries = ep.get("entries", [])
    print(f"  entries: {len(entries)}")
    if entries:
        last = entries[-1]
        print(
            f"  last ritual: {last.get('ritual_id', '?')} at {last.get('timestamp', '?')}"
        )


def action_validate(memory_dir: str) -> None:
    """Validate all tiers and report warnings."""
    mm = MemoryManager(memory_dir)
    all_warnings: dict[str, list[str]] = {}

    for tier_name, defaults, limits in [
        ("core", DEFAULT_CORE, None),
        (
            "semantic",
            DEFAULT_SEMANTIC,
            {
                "evolution_log": SIZE_LIMITS["evolution_log"],
                "source_intelligence": SIZE_LIMITS["source_intelligence"],
                "emerging_interests": SIZE_LIMITS["emerging_interests"],
            },
        ),
        ("episodic", DEFAULT_EPISODIC, {"entries": SIZE_LIMITS["entries"]}),
    ]:
        tier_path = os.path.join(
            os.path.expanduser(memory_dir), f"the_only_{tier_name}.json"
        )
        data = load_json(tier_path, copy.deepcopy(defaults))
        repaired, warnings = validate_tier(data, defaults, limits)
        all_warnings[tier_name] = warnings
        if repaired != data:
            save_json(tier_path, repaired)

    total = sum(len(w) for w in all_warnings.values())
    if total == 0:
        print("✅ All tiers valid — no warnings")
    else:
        print(f"⚠️  {total} warning(s) across tiers:")
        for tier_name, warnings in all_warnings.items():
            for w in warnings:
                print(f"  [{tier_name}] {w}")


def action_maintain(memory_dir: str) -> None:
    """Run maintenance cycle."""
    mm = MemoryManager(memory_dir)
    report = mm.run_maintenance()
    print("🔧 Maintenance Report:")
    print(f"  compression_needed: {report['compression_needed']}")
    if report["compression_reason"]:
        print(f"  compression_reason: {report['compression_reason']}")
    print(f"  compressed: {report['compressed']}")
    print(f"  projections_written: {report['projections_written']}")


def action_project(memory_dir: str) -> None:
    """Generate markdown projections."""
    mm = MemoryManager(memory_dir)
    all_data = mm.load_all()
    write_projections(
        all_data["core"],
        all_data["semantic"],
        all_data["episodic"],
        memory_dir,
    )
    print("✅ Projections generated")


def action_status(memory_dir: str) -> None:
    """Print tier stats."""
    expanded = os.path.expanduser(memory_dir)

    tiers = [
        ("core", os.path.join(expanded, "the_only_core.json")),
        ("semantic", os.path.join(expanded, "the_only_semantic.json")),
        ("episodic", os.path.join(expanded, "the_only_episodic.json")),
    ]

    print("📊 Memory Status:")
    for name, path in tiers:
        exists = os.path.exists(path)
        if exists:
            stat = os.stat(path)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            data = load_json(path, {})

            # Count entries for relevant fields
            counts: list[str] = []
            if name == "episodic":
                counts.append(f"entries={len(data.get('entries', []))}")
            elif name == "semantic":
                counts.append(f"sources={len(data.get('source_intelligence', {}))}")
                counts.append(f"evo_log={len(data.get('evolution_log', []))}")
                counts.append(f"interests={len(data.get('emerging_interests', []))}")
            elif name == "core":
                focus = data.get("identity", {}).get("current_focus", [])
                counts.append(f"focus={len(focus)}")

            counts_str = ", ".join(counts) if counts else ""
            print(f"  [{name}] {path}")
            print(f"    size={size}B, modified={mtime}")
            if counts_str:
                print(f"    {counts_str}")
        else:
            print(f"  [{name}] {path} — NOT FOUND (will use defaults)")

    # Compression status
    mm = MemoryManager(memory_dir)
    needs, reason = mm.episodic.needs_compression()
    if needs:
        print(f"  ⚠️  Compression needed: {reason}")
    else:
        print("  ✅ No compression needed")


# ══════════════════════════════════════════════════════════════
# SELF-TESTS
# ══════════════════════════════════════════════════════════════


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

    with tempfile.TemporaryDirectory(prefix="memory_v2_test_") as tmpdir:
        print("🧪 Running self-tests...")
        print(f"   temp dir: {tmpdir}")
        print()

        # ── Test 1: validate_tier repairs missing fields ──
        print("── validate_tier: repair missing fields ──")
        incomplete = {"version": "2.0"}
        repaired, warnings = validate_tier(incomplete, DEFAULT_CORE)
        _assert("identity" in repaired, "identity key filled")
        _assert("reading_preferences" in repaired, "reading_preferences key filled")
        _assert("current_focus" in repaired["identity"], "nested current_focus filled")
        _assert(len(warnings) > 0, "warnings generated for missing keys")

        # ── Test 2: validate_tier trims oversized lists ──
        print()
        print("── validate_tier: trim oversized lists ──")
        oversized = copy.deepcopy(DEFAULT_SEMANTIC)
        oversized["evolution_log"] = [{"i": i} for i in range(30)]
        repaired, warnings = validate_tier(
            oversized, DEFAULT_SEMANTIC, {"evolution_log": SIZE_LIMITS["evolution_log"]}
        )
        _assert(
            len(repaired["evolution_log"]) == 20,
            f"evolution_log trimmed to 20 (was 30)",
        )
        _assert(
            repaired["evolution_log"][0]["i"] == 10,
            "oldest entries removed (kept 10-29)",
        )
        _assert(any("Trimmed" in w for w in warnings), "trim warning generated")

        # ── Test 3: validate_tier trims oversized dicts ──
        print()
        print("── validate_tier: trim oversized dicts ──")
        oversized_dict = copy.deepcopy(DEFAULT_SEMANTIC)
        oversized_dict["source_intelligence"] = {
            f"source_{i}": {"quality_avg": float(i)} for i in range(35)
        }
        repaired, warnings = validate_tier(
            oversized_dict,
            DEFAULT_SEMANTIC,
            {"source_intelligence": SIZE_LIMITS["source_intelligence"]},
        )
        _assert(
            len(repaired["source_intelligence"]) == 30,
            f"source_intelligence trimmed to 30 (was 35)",
        )
        # Should keep highest quality (source_5..source_34 → keeps top 30)
        _assert(
            "source_34" in repaired["source_intelligence"],
            "highest quality source retained",
        )
        _assert(
            "source_0" not in repaired["source_intelligence"],
            "lowest quality source removed",
        )

        # ── Test 4: CoreLayer read/write round-trip ──
        print()
        print("── CoreLayer: read/write round-trip ──")
        core = CoreLayer(tmpdir)
        data = core.read()
        _assert(data["version"] == "2.0", "default version on fresh read")
        _assert(data["identity"]["current_focus"] == [], "default focus is empty list")

        core.update_identity(
            {"current_focus": ["AI", "music"], "professional_domain": "engineering"}
        )
        data2 = core.read()
        _assert(
            data2["identity"]["current_focus"] == ["AI", "music"], "identity updated"
        )
        _assert(
            data2["identity"]["professional_domain"] == "engineering", "domain updated"
        )
        _assert(data2["last_validated"] != "", "last_validated set after update")

        core.update_reading_preferences({"emotional_vibe": "contemplative"})
        data3 = core.read()
        _assert(
            data3["reading_preferences"]["emotional_vibe"] == "contemplative",
            "prefs updated",
        )

        core.touch_validated()
        data4 = core.read()
        _assert(
            data4["last_validated"] != data2["last_validated"],
            "touch_validated updates timestamp",
        )

        # ── Test 5: EpisodicLayer FIFO enforcement ──
        print()
        print("── EpisodicLayer: FIFO enforcement ──")
        ep = EpisodicLayer(tmpdir)
        for i in range(60):
            ep.append_entry(
                {
                    "ritual_id": f"r{i}",
                    "timestamp": _now_iso(),
                    "avg_quality_score": 5.0,
                    "engagement": 3.0,
                }
            )
        data = ep.read()
        entries = data["entries"]
        _assert(
            len(entries) == 50,
            f"FIFO: 50 entries after writing 60 (got {len(entries)})",
        )
        _assert(entries[0]["ritual_id"] == "r10", "oldest entry is r10 (r0-r9 trimmed)")
        _assert(entries[-1]["ritual_id"] == "r59", "newest entry is r59")

        # ── Test 6: needs_compression detection ──
        print()
        print("── EpisodicLayer: needs_compression ──")

        # Test variance trigger: >25 entries with high engagement variance
        ep2 = EpisodicLayer(tmpdir)
        # Reset
        ep2.write(copy.deepcopy(DEFAULT_EPISODIC))
        for i in range(30):
            ep2.append_entry(
                {
                    "ritual_id": f"var{i}",
                    "timestamp": _now_iso(),
                    "avg_quality_score": 5.0,
                    "engagement": 10.0 if i % 2 == 0 else 0.0,
                }
            )
        needs, reason = ep2.needs_compression()
        _assert(needs is True, f"variance trigger fires (reason: {reason})")
        _assert("variance" in reason, "reason mentions variance")

        # Test forced trigger: >50
        ep3_data = copy.deepcopy(DEFAULT_EPISODIC)
        ep3_data["entries"] = [
            {"ritual_id": f"f{i}", "avg_quality_score": 5.0, "engagement": 3.0}
            for i in range(51)
        ]
        ep3 = EpisodicLayer(tmpdir)
        ep3.write(ep3_data)
        needs, reason = ep3.needs_compression()
        _assert(needs is True, f"forced trigger fires (reason: {reason})")
        _assert("forced" in reason, "reason mentions forced")

        # Test emergency trigger: 3 consecutive low quality
        ep4 = EpisodicLayer(tmpdir)
        ep4.write(copy.deepcopy(DEFAULT_EPISODIC))
        for i in range(5):
            ep4.append_entry(
                {
                    "ritual_id": f"low{i}",
                    "timestamp": _now_iso(),
                    "avg_quality_score": 0.5,
                    "engagement": 3.0,
                }
            )
        needs, reason = ep4.needs_compression()
        _assert(needs is True, f"emergency trigger fires (reason: {reason})")
        _assert("emergency" in reason, "reason mentions emergency")

        # Test no compression needed
        ep5 = EpisodicLayer(tmpdir)
        ep5.write(copy.deepcopy(DEFAULT_EPISODIC))
        for i in range(10):
            ep5.append_entry(
                {
                    "ritual_id": f"ok{i}",
                    "timestamp": _now_iso(),
                    "avg_quality_score": 7.0,
                    "engagement": 3.0,
                }
            )
        needs, reason = ep5.needs_compression()
        _assert(needs is False, "no compression needed for small healthy buffer")

        # ── Test 7: SemanticLayer operations ──
        print()
        print("── SemanticLayer: operations ──")
        sem = SemanticLayer(tmpdir)
        data = sem.read()
        _assert(data["version"] == "2.0", "semantic default version")

        sem.update_fetch_strategy({"primary_sources": ["arxiv", "hackernews"]})
        data = sem.read()
        _assert(
            data["fetch_strategy"]["primary_sources"] == ["arxiv", "hackernews"],
            "fetch strategy updated",
        )

        for i in range(25):
            sem.add_evolution_entry(
                {"timestamp": _now_iso(), "description": f"change {i}"}
            )
        data = sem.read()
        _assert(
            len(data["evolution_log"]) == 20,
            f"evolution_log capped at 20 (got {len(data['evolution_log'])})",
        )

        for i in range(35):
            sem.update_source_intelligence(
                f"src_{i}", {"quality_avg": float(i), "hits": i * 10}
            )
        data = sem.read()
        _assert(
            len(data["source_intelligence"]) == 30,
            f"source_intelligence capped at 30 (got {len(data['source_intelligence'])})",
        )

        si = sem.get_source_intelligence()
        _assert(isinstance(si, dict), "get_source_intelligence returns dict")

        # Test emerging interests with faded trimming
        sem2 = SemanticLayer(tmpdir)
        sem2_data = sem2.read()
        sem2_data["emerging_interests"] = []
        sem2.write(sem2_data)

        for i in range(8):
            sem2.add_emerging_interest({"name": f"interest_{i}", "status": "active"})
        sem2.add_emerging_interest({"name": "faded_one", "status": "faded"})
        sem2.add_emerging_interest({"name": "faded_two", "status": "faded"})
        # Now at 10. Adding one more should trim faded first.
        sem2.add_emerging_interest({"name": "new_hot", "status": "active"})
        data = sem2.read()
        interests = data["emerging_interests"]
        _assert(
            len(interests) <= 10,
            f"emerging_interests capped at 10 (got {len(interests)})",
        )
        names = [i["name"] for i in interests]
        _assert("new_hot" in names, "new interest added")

        # ── Test 8: generate_context_md ──
        print()
        print("── generate_context_md: produces valid markdown ──")
        test_core = copy.deepcopy(DEFAULT_CORE)
        test_core["identity"]["current_focus"] = ["AI safety", "music theory"]
        test_core["identity"]["knowledge_level"] = {
            "AI": "advanced",
            "music": "intermediate",
        }
        test_core["reading_preferences"]["emotional_vibe"] = "contemplative"

        test_semantic = copy.deepcopy(DEFAULT_SEMANTIC)
        test_semantic["fetch_strategy"]["primary_sources"] = ["arxiv", "HN"]
        test_semantic["fetch_strategy"]["ratio"] = {
            "tech": 60,
            "serendipity": 20,
            "research": 20,
        }
        test_semantic["source_intelligence"] = {
            "arxiv": {"quality_avg": 8.5, "hits": 100},
            "HN": {"quality_avg": 7.2, "hits": 50},
        }
        test_semantic["evolution_log"] = [
            {"timestamp": "2025-01-01T00:00:00Z", "description": "Initial setup"},
        ]

        md = generate_context_md(test_core, test_semantic)
        _assert("# The Only — Context Map" in md, "has title header")
        _assert("AI safety" in md, "contains focus topics")
        _assert("contemplative" in md, "contains emotional vibe")
        _assert("arxiv" in md, "contains sources")
        _assert("## 1. Cognitive State" in md, "has section 1")
        _assert("## 2. Dynamic Fetch Strategy" in md, "has section 2")
        _assert("## 3. Engagement Tracker" in md, "has section 3")
        _assert("## 4. Source Intelligence (Top 5)" in md, "has section 4")
        _assert("## 5. Evolution Log (Last 10)" in md, "has section 5")

        # ── Test 9: generate_meta_md ──
        print()
        print("── generate_meta_md: produces valid markdown ──")
        test_episodic = copy.deepcopy(DEFAULT_EPISODIC)
        test_episodic["entries"] = [
            {"ritual_id": "r1", "self_notes": "Need more variety"},
            {"ritual_id": "r2", "self_notes": "Quality improving"},
        ]
        test_semantic["emerging_interests"] = [
            {"name": "quantum computing", "status": "active"},
        ]
        test_semantic["synthesis_effectiveness"] = {"brevity": "improving"}

        meta = generate_meta_md(test_semantic, test_episodic)
        _assert("# Ruby — Meta-Learning Notes" in meta, "has meta title")
        _assert("## 1. Synthesis Style Insights" in meta, "has section 1")
        _assert("## 2. Temporal Patterns" in meta, "has section 2")
        _assert("## 3. Emerging Interests" in meta, "has section 3")
        _assert("## 4. Recent Self-Notes" in meta, "has section 4")
        _assert("Need more variety" in meta, "contains self-note content")
        _assert("quantum computing" in meta, "contains emerging interest")

        # ── Test 10: MemoryManager round-trip ──
        print()
        print("── MemoryManager: round-trip ──")
        mm = MemoryManager(tmpdir)
        mm.episodic.write(copy.deepcopy(DEFAULT_EPISODIC))
        mm.core.write(copy.deepcopy(DEFAULT_CORE))
        mm.semantic.write(copy.deepcopy(DEFAULT_SEMANTIC))
        all_data = mm.load_all()
        _assert("core" in all_data, "load_all has core key")
        _assert("semantic" in all_data, "load_all has semantic key")
        _assert("episodic" in all_data, "load_all has episodic key")

        mm.update_core({"identity": {"current_focus": ["testing"]}})
        snapshot = mm.get_context_snapshot()
        _assert(
            snapshot["identity"]["current_focus"] == ["testing"],
            "context snapshot reflects update",
        )

        mm.save_episodic_entry(
            {"ritual_id": "test_r1", "avg_quality_score": 7.0, "engagement": 4.0}
        )
        snapshot2 = mm.get_context_snapshot()
        _assert(snapshot2["episodic_count"] == 1, "episodic count is 1 after save")

        # ── Test 11: write_projections ──
        print()
        print("── write_projections: files created ──")
        all_data = mm.load_all()
        write_projections(
            all_data["core"], all_data["semantic"], all_data["episodic"], tmpdir
        )
        ctx_path = os.path.join(tmpdir, "the_only_context.md")
        meta_path = os.path.join(tmpdir, "the_only_meta.md")
        _assert(os.path.exists(ctx_path), "context.md created")
        _assert(os.path.exists(meta_path), "meta.md created")
        with open(ctx_path, "r", encoding="utf-8") as f:
            ctx_content = f.read()
        _assert(
            "# The Only — Context Map" in ctx_content, "context.md has correct header"
        )

        # ── Test 12: run_maintenance ──
        print()
        print("── MemoryManager: run_maintenance ──")
        report = mm.run_maintenance()
        _assert(isinstance(report, dict), "maintenance returns dict")
        _assert("compression_needed" in report, "report has compression_needed")
        _assert("projections_written" in report, "report has projections_written")
        _assert(report["projections_written"] is True, "projections were written")

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
# MAIN
# ══════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Memory v2.0 — Three-Layer Memory System for the_only"
    )
    parser.add_argument(
        "--action",
        choices=["read-all", "validate", "maintain", "project", "status", "test"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--memory-dir",
        default="~/memory",
        help="Memory directory (default: ~/memory)",
    )
    args = parser.parse_args()

    if args.action == "test":
        action_test()
    elif args.action == "read-all":
        action_read_all(args.memory_dir)
    elif args.action == "validate":
        action_validate(args.memory_dir)
    elif args.action == "maintain":
        action_maintain(args.memory_dir)
    elif args.action == "project":
        action_project(args.memory_dir)
    elif args.action == "status":
        action_status(args.memory_dir)


if __name__ == "__main__":
    main()
