#!/usr/bin/env python3
"""
Source Intelligence Graph
─────────────────────────
Manages source quality profiles, pre-ranking, and redundancy
tracking for the_only information gathering pipeline.

Sources are scored by expected yield:
  expected_yield = quality_avg × reliability × freshness_factor × (1 - max_redundancy)

Actions:
  rank    — Pre-rank sources by expected yield
  status  — Show all source profile summaries
  update  — Record a quality score for a source
  fail    — Record a fetch failure for a source
  test    — Run self-tests
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

SEMANTIC_FILE = os.path.expanduser("~/memory/the_only_semantic.json")


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

FRESHNESS_FACTOR: dict[str, float] = {
    "hourly": 1.0,
    "daily": 1.0,
    "weekly": 0.7,
    "monthly": 0.5,
    "unknown": 0.5,
}

SKIP_THRESHOLD: float = 2.0
MAX_QUALITY_SCORES: int = 20
MAX_SOURCES: int = 30

DEFAULT_SOURCE_PROFILE: dict = {
    "quality_avg": 5.0,
    "quality_scores": [],
    "reliability": 0.5,
    "consecutive_failures": 0,
    "depth": "medium",
    "bias": "",
    "freshness": "unknown",
    "exclusivity": 0.0,
    "best_for": "",
    "redundancy_with": {},
    "last_evaluated": "",
}


# ══════════════════════════════════════════════════════════════
# JSON I/O HELPERS
# ══════════════════════════════════════════════════════════════


def load_json(path: str, default: dict | None = None) -> dict:
    """Load JSON from *path*, returning *default* on missing/corrupt files."""
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                result = json.load(f)
                if isinstance(result, dict):
                    return result
        except json.JSONDecodeError as e:
            print(f"⚠️  {path} is not valid JSON: {e}", file=sys.stderr)
    return default


def save_json(path: str, data: dict) -> None:
    """Write *data* as pretty-printed JSON to *path*."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════
# SOURCE PROFILE DATACLASS
# ══════════════════════════════════════════════════════════════


@dataclass
class SourceProfile:
    """Quality and metadata profile for a single information source."""

    name: str
    quality_avg: float = 5.0
    quality_scores: list[float] = field(default_factory=list)
    reliability: float = 0.5
    consecutive_failures: int = 0
    depth: str = "medium"  # shallow, medium, deep
    bias: str = ""
    freshness: str = "unknown"  # hourly, daily, weekly, monthly, unknown
    exclusivity: float = 0.0
    best_for: str = ""
    redundancy_with: dict[str, float] = field(default_factory=dict)
    last_evaluated: str = ""

    @classmethod
    def from_dict(cls, name: str, data: dict) -> SourceProfile:
        """Create a SourceProfile from a dict, filling missing keys with defaults."""
        merged = dict(DEFAULT_SOURCE_PROFILE)
        merged.update(data)
        return cls(
            name=name,
            quality_avg=float(merged["quality_avg"]),
            quality_scores=list(merged["quality_scores"]),
            reliability=float(merged["reliability"]),
            consecutive_failures=int(merged["consecutive_failures"]),
            depth=str(merged["depth"]),
            bias=str(merged["bias"]),
            freshness=str(merged["freshness"]),
            exclusivity=float(merged["exclusivity"]),
            best_for=str(merged["best_for"]),
            redundancy_with=dict(merged["redundancy_with"]),
            last_evaluated=str(merged["last_evaluated"]),
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict (excludes name, which is the key)."""
        return {
            "quality_avg": self.quality_avg,
            "quality_scores": self.quality_scores,
            "reliability": self.reliability,
            "consecutive_failures": self.consecutive_failures,
            "depth": self.depth,
            "bias": self.bias,
            "freshness": self.freshness,
            "exclusivity": self.exclusivity,
            "best_for": self.best_for,
            "redundancy_with": self.redundancy_with,
            "last_evaluated": self.last_evaluated,
        }


# ══════════════════════════════════════════════════════════════
# SOURCE GRAPH
# ══════════════════════════════════════════════════════════════


class SourceGraph:
    """In-memory graph of source intelligence profiles with pre-ranking."""

    def __init__(self, source_intelligence: dict | None = None) -> None:
        """Initialize from the source_intelligence dict stored in semantic.json."""
        self._profiles: dict[str, SourceProfile] = {}
        if source_intelligence:
            for name, data in source_intelligence.items():
                self._profiles[name] = SourceProfile.from_dict(name, data)

    # ── queries ──────────────────────────────────────────────

    def get_profile(self, name: str) -> SourceProfile | None:
        """Get a source's profile by name, or None if not found."""
        return self._profiles.get(name)

    def all_profiles(self) -> list[SourceProfile]:
        """Return all source profiles, sorted by quality_avg descending."""
        return sorted(
            self._profiles.values(), key=lambda p: p.quality_avg, reverse=True
        )

    def pre_rank(
        self, already_fetched: list[str] | None = None
    ) -> list[tuple[str, float]]:
        """Pre-rank sources by expected yield.

        Returns list of (source_name, expected_yield) sorted descending.
        Sources below SKIP_THRESHOLD are excluded UNLESS that would leave
        fewer than 3 results — in which case the best below-threshold
        sources are promoted to reach 3.
        """
        if not self._profiles:
            return []

        already_fetched = already_fetched or []
        results: list[tuple[str, float]] = []

        for name, profile in self._profiles.items():
            ff = FRESHNESS_FACTOR.get(profile.freshness, 0.5)
            max_redundancy = 0.0
            for fetched in already_fetched:
                max_redundancy = max(
                    max_redundancy,
                    profile.redundancy_with.get(fetched, 0.0),
                )
            yield_score = (
                profile.quality_avg * profile.reliability * ff * (1 - max_redundancy)
            )
            results.append((name, yield_score))

        results.sort(key=lambda x: x[1], reverse=True)

        above = [(n, y) for n, y in results if y >= SKIP_THRESHOLD]
        below = [(n, y) for n, y in results if y < SKIP_THRESHOLD]

        # Ensure at least 3 sources pass through for category diversity
        if len(above) < 3 and below:
            above.extend(below[: 3 - len(above)])

        return above

    # ── mutations ────────────────────────────────────────────

    def record_success(self, name: str, quality_score: float) -> None:
        """Record a successful fetch with a quality score.

        - Appends to quality_scores (capped at MAX_QUALITY_SCORES)
        - Recalculates quality_avg
        - Resets consecutive_failures to 0
        - Updates reliability upward
        - Updates last_evaluated
        """
        profile = self._ensure_profile(name)
        profile.quality_scores.append(quality_score)
        if len(profile.quality_scores) > MAX_QUALITY_SCORES:
            profile.quality_scores = profile.quality_scores[-MAX_QUALITY_SCORES:]
        profile.quality_avg = sum(profile.quality_scores) / len(profile.quality_scores)
        profile.consecutive_failures = 0
        count = len(profile.quality_scores)
        profile.reliability = min(
            1.0, (profile.reliability * count + 1.0) / (count + 1)
        )
        profile.last_evaluated = _today()

    def record_failure(self, name: str) -> None:
        """Record a failed fetch.

        - Increments consecutive_failures
        - Decreases reliability by 0.1 (floored at 0.0)
        - Updates last_evaluated
        """
        profile = self._ensure_profile(name)
        profile.consecutive_failures += 1
        profile.reliability = max(0.0, profile.reliability - 0.1)
        profile.last_evaluated = _today()

    def update_quality(self, name: str, score: float) -> None:
        """Add a quality score without changing failure state."""
        profile = self._ensure_profile(name)
        profile.quality_scores.append(score)
        if len(profile.quality_scores) > MAX_QUALITY_SCORES:
            profile.quality_scores = profile.quality_scores[-MAX_QUALITY_SCORES:]
        profile.quality_avg = sum(profile.quality_scores) / len(profile.quality_scores)
        profile.last_evaluated = _today()

    def update_redundancy(self, name_a: str, name_b: str, overlap: float) -> None:
        """Update bidirectional redundancy between two sources."""
        pa = self._ensure_profile(name_a)
        pb = self._ensure_profile(name_b)
        pa.redundancy_with[name_b] = overlap
        pb.redundancy_with[name_a] = overlap

    def add_source(self, name: str, profile: SourceProfile | None = None) -> None:
        """Add a new source. If at MAX_SOURCES, remove the lowest quality_avg source."""
        if name in self._profiles:
            return
        if len(self._profiles) >= MAX_SOURCES:
            worst = min(self._profiles.values(), key=lambda p: p.quality_avg)
            del self._profiles[worst.name]
        if profile is None:
            profile = SourceProfile.from_dict(name, {})
        self._profiles[name] = profile

    def remove_source(self, name: str) -> None:
        """Remove a source from the graph."""
        self._profiles.pop(name, None)

    # ── serialization ────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize back to the source_intelligence dict format for semantic.json."""
        return {name: profile.to_dict() for name, profile in self._profiles.items()}

    @classmethod
    def load_from_file(cls, path: str | None = None) -> SourceGraph:
        """Load SourceGraph from semantic.json file."""
        path = path or SEMANTIC_FILE
        data = load_json(path, default={})
        source_intelligence = data.get("source_intelligence", {})
        return cls(source_intelligence)

    def save_to_file(self, path: str | None = None) -> None:
        """Save back to semantic.json (only updates the source_intelligence key)."""
        path = path or SEMANTIC_FILE
        data = load_json(path, default={})
        data["source_intelligence"] = self.to_dict()
        save_json(path, data)

    # ── internal helpers ─────────────────────────────────────

    def _ensure_profile(self, name: str) -> SourceProfile:
        """Return existing profile or create a default one."""
        if name not in self._profiles:
            self._profiles[name] = SourceProfile.from_dict(name, {})
        return self._profiles[name]


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════


def _today() -> str:
    """Return today's date as ISO string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ══════════════════════════════════════════════════════════════
# CLI ACTIONS
# ══════════════════════════════════════════════════════════════


def action_rank(args: argparse.Namespace) -> None:
    """Pre-rank sources and display expected yields."""
    graph = SourceGraph.load_from_file()
    fetched = args.fetched.split(",") if args.fetched else []
    ranked = graph.pre_rank(already_fetched=fetched)

    if not ranked:
        print("📭 No sources in graph.")
        return

    print(f"📊 Source pre-ranking ({len(ranked)} sources):\n")
    for i, (name, yield_score) in enumerate(ranked, 1):
        profile = graph.get_profile(name)
        assert profile is not None
        tag = "⏭️  SKIP" if yield_score < SKIP_THRESHOLD else "   "
        print(
            f"  {i:>2}. {name:<20} yield={yield_score:.2f}  "
            f"q={profile.quality_avg:.1f}  r={profile.reliability:.2f}  "
            f"f={profile.freshness:<8} {tag}"
        )


def action_status(args: argparse.Namespace) -> None:
    """Show all source profile summaries."""
    graph = SourceGraph.load_from_file()
    profiles = graph.all_profiles()

    if not profiles:
        print("📭 No sources in graph.")
        return

    print(f"📈 Source Intelligence Graph — {len(profiles)} sources\n")
    for p in profiles:
        scores_str = (
            f"{len(p.quality_scores)} scores" if p.quality_scores else "no scores"
        )
        redundancies = (
            ", ".join(f"{k}:{v:.2f}" for k, v in p.redundancy_with.items())
            if p.redundancy_with
            else "none"
        )
        print(f"  {p.name}")
        print(
            f"    quality_avg={p.quality_avg:.1f} ({scores_str})  "
            f"reliability={p.reliability:.2f}  freshness={p.freshness}"
        )
        print(
            f"    depth={p.depth}  bias={p.bias or '—'}  "
            f"exclusivity={p.exclusivity:.1f}"
        )
        print(f"    best_for={p.best_for or '—'}  redundancy=[{redundancies}]")
        print(
            f"    failures={p.consecutive_failures}  "
            f"last_evaluated={p.last_evaluated or '—'}"
        )
        print()


def action_update(args: argparse.Namespace) -> None:
    """Record a quality score for a source."""
    if not args.source:
        print("❌ --source is required for update", file=sys.stderr)
        sys.exit(1)
    if args.quality is None:
        print("❌ --quality is required for update", file=sys.stderr)
        sys.exit(1)

    graph = SourceGraph.load_from_file()
    graph.record_success(args.source, args.quality)
    graph.save_to_file()
    profile = graph.get_profile(args.source)
    assert profile is not None
    print(
        f"✅ {args.source}: quality_avg={profile.quality_avg:.2f}  "
        f"reliability={profile.reliability:.2f}  "
        f"scores={len(profile.quality_scores)}"
    )


def action_fail(args: argparse.Namespace) -> None:
    """Record a failure for a source."""
    if not args.source:
        print("❌ --source is required for fail", file=sys.stderr)
        sys.exit(1)

    graph = SourceGraph.load_from_file()
    graph.record_failure(args.source)
    graph.save_to_file()
    profile = graph.get_profile(args.source)
    assert profile is not None
    print(
        f"⚠️  {args.source}: reliability={profile.reliability:.2f}  "
        f"consecutive_failures={profile.consecutive_failures}"
    )


# ══════════════════════════════════════════════════════════════
# SELF-TESTS
# ══════════════════════════════════════════════════════════════


def action_test(args: argparse.Namespace) -> None:
    """Run self-tests."""
    passed = 0
    failed = 0

    def assert_eq(label: str, actual: object, expected: object) -> None:
        nonlocal passed, failed
        if actual == expected:
            passed += 1
            print(f"  ✅ {label}")
        else:
            failed += 1
            print(f"  ❌ {label}: expected {expected!r}, got {actual!r}")

    def assert_true(label: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {label}")
        else:
            failed += 1
            print(f"  ❌ {label}: condition was False")

    print("🧪 Source Graph Self-Tests\n")

    # ── Test 1: pre_rank ordering ────────────────────────────
    print("Test 1: pre_rank ordering")
    g = SourceGraph(
        {
            "high": {"quality_avg": 9.0, "reliability": 1.0, "freshness": "hourly"},
            "mid": {"quality_avg": 5.0, "reliability": 0.8, "freshness": "daily"},
            "low": {"quality_avg": 3.0, "reliability": 0.6, "freshness": "weekly"},
        }
    )
    ranked = g.pre_rank()
    names = [n for n, _ in ranked]
    assert_eq("highest first", names[0], "high")
    assert_true("mid before low", names.index("mid") < names.index("low"))
    print()

    # ── Test 2: skip threshold ───────────────────────────────
    print("Test 2: skip threshold")
    g2 = SourceGraph(
        {
            "good": {"quality_avg": 8.0, "reliability": 1.0, "freshness": "daily"},
            "ok": {"quality_avg": 5.0, "reliability": 0.8, "freshness": "daily"},
            "decent": {"quality_avg": 4.0, "reliability": 0.7, "freshness": "weekly"},
            "bad": {"quality_avg": 1.0, "reliability": 0.2, "freshness": "unknown"},
        }
    )
    ranked2 = g2.pre_rank()
    ranked_names = [n for n, _ in ranked2]
    # "bad" yield = 1.0 * 0.2 * 0.5 * 1.0 = 0.1  → below threshold
    # With 3 above threshold, "bad" should be excluded
    assert_true("bad excluded when enough above threshold", "bad" not in ranked_names)
    assert_true("at least 3 sources", len(ranked2) >= 3)
    print()

    # ── Test 3: record_success ───────────────────────────────
    print("Test 3: record_success")
    g3 = SourceGraph(
        {"src": {"quality_avg": 5.0, "reliability": 0.5, "consecutive_failures": 3}}
    )
    g3.record_success("src", 8.0)
    p3 = g3.get_profile("src")
    assert p3 is not None
    assert_eq("quality_avg updated", p3.quality_avg, 8.0)
    assert_eq("consecutive_failures reset", p3.consecutive_failures, 0)
    assert_true("reliability increased", p3.reliability > 0.5)
    assert_true("last_evaluated set", p3.last_evaluated != "")
    print()

    # ── Test 4: record_failure ───────────────────────────────
    print("Test 4: record_failure")
    g4 = SourceGraph(
        {"src": {"quality_avg": 6.0, "reliability": 0.8, "consecutive_failures": 1}}
    )
    g4.record_failure("src")
    p4 = g4.get_profile("src")
    assert p4 is not None
    assert_eq("consecutive_failures incremented", p4.consecutive_failures, 2)
    assert_true("reliability decreased", abs(p4.reliability - 0.7) < 0.001)
    print()

    # ── Test 5: redundancy affects yield ─────────────────────
    print("Test 5: redundancy reduces yield")
    g5 = SourceGraph(
        {
            "alpha": {
                "quality_avg": 7.0,
                "reliability": 1.0,
                "freshness": "daily",
                "redundancy_with": {"beta": 0.5},
            },
            "beta": {
                "quality_avg": 7.0,
                "reliability": 1.0,
                "freshness": "daily",
                "redundancy_with": {"alpha": 0.5},
            },
        }
    )
    ranked_no_fetch = g5.pre_rank()
    ranked_with_fetch = g5.pre_rank(already_fetched=["alpha"])
    yield_beta_no = dict(ranked_no_fetch).get("beta", 0)
    yield_beta_with = dict(ranked_with_fetch).get("beta", 0)
    assert_true("beta yield lower when alpha fetched", yield_beta_with < yield_beta_no)
    print()

    # ── Test 6: MAX_QUALITY_SCORES cap ───────────────────────
    print("Test 6: MAX_QUALITY_SCORES cap")
    g6 = SourceGraph({"src": {}})
    for i in range(25):
        g6.update_quality("src", float(i))
    p6 = g6.get_profile("src")
    assert p6 is not None
    assert_eq("capped at 20", len(p6.quality_scores), MAX_QUALITY_SCORES)
    assert_eq("keeps most recent", p6.quality_scores[0], 5.0)
    assert_eq("last score is 24", p6.quality_scores[-1], 24.0)
    print()

    # ── Test 7: MAX_SOURCES cap ──────────────────────────────
    print("Test 7: MAX_SOURCES cap")
    sources = {f"s{i}": {"quality_avg": float(i)} for i in range(MAX_SOURCES)}
    g7 = SourceGraph(sources)
    assert_eq("at max", len(g7.all_profiles()), MAX_SOURCES)
    g7.add_source("s_new", SourceProfile.from_dict("s_new", {"quality_avg": 99.0}))
    assert_eq("still at max after add", len(g7.all_profiles()), MAX_SOURCES)
    assert_true("s0 removed (lowest quality)", g7.get_profile("s0") is None)
    assert_true("s_new added", g7.get_profile("s_new") is not None)
    print()

    # ── Test 8: from_dict / to_dict round-trip ───────────────
    print("Test 8: from_dict / to_dict round-trip")
    original = {
        "quality_avg": 7.5,
        "quality_scores": [7.0, 8.0],
        "reliability": 0.9,
        "consecutive_failures": 1,
        "depth": "deep",
        "bias": "academic",
        "freshness": "weekly",
        "exclusivity": 0.3,
        "best_for": "research papers",
        "redundancy_with": {"arxiv": 0.4},
        "last_evaluated": "2026-03-25",
    }
    profile = SourceProfile.from_dict("test_src", original)
    roundtripped = profile.to_dict()
    assert_eq("round-trip match", roundtripped, original)
    print()

    # ── Test 9: empty graph ──────────────────────────────────
    print("Test 9: empty graph")
    g9 = SourceGraph()
    assert_eq("pre_rank on empty", g9.pre_rank(), [])
    assert_eq("all_profiles on empty", g9.all_profiles(), [])
    assert_eq("get_profile on empty", g9.get_profile("x"), None)
    print()

    # ── Summary ──────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'=' * 40}")
    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
        sys.exit(1)
    else:
        print("  ✨ All clear!")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Source Intelligence Graph — quality tracking & pre-ranking",
    )
    parser.add_argument(
        "--action",
        choices=["rank", "status", "update", "fail", "test"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--fetched",
        default="",
        help="Comma-separated list of already-fetched sources (for rank)",
    )
    parser.add_argument("--source", default="", help="Source name (for update/fail)")
    parser.add_argument(
        "--quality", type=float, default=None, help="Quality score 0-10 (for update)"
    )
    args = parser.parse_args()

    actions = {
        "rank": action_rank,
        "status": action_status,
        "update": action_update,
        "fail": action_fail,
        "test": action_test,
    }
    actions[args.action](args)


if __name__ == "__main__":
    main()
