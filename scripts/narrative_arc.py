#!/usr/bin/env python3
"""
The ONLY — Narrative Arc Engine
Orders curated articles into a 5-position story arc:
Opening → Deep Dive → Surprise → Contrarian → Synthesis.

Actions:
  build   — Build arc from JSON payload, output ArcPlan as JSON
  preview — Build arc, output formatted preview text
  test    — Run self-tests
"""

from __future__ import annotations

import json
import sys
import argparse
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ArcPosition(Enum):
    """Narrative arc positions, ordered as they appear in a ritual."""

    OPENING = "Opening"
    DEEP_DIVE = "Deep Dive"
    SURPRISE = "Surprise"
    CONTRARIAN = "Contrarian"
    SYNTHESIS = "Synthesis"

    @property
    def label(self) -> str:
        """Human-readable display label."""
        return self.value


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CandidateItem:
    """A scored article candidate entering the arc selection pipeline."""

    title: str
    url: str = ""
    composite_score: float = 0.0
    relevance_score: float = 0.0
    depth_score: float = 0.0
    insight_density_score: float = 0.0
    uniqueness_score: float = 0.0
    categories: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    source: str = ""
    is_serendipity: bool = False
    is_echo: bool = False
    curation_reason: str = ""


@dataclass
class ArcItem:
    """A candidate that has been placed into a narrative position."""

    candidate: CandidateItem
    position: ArcPosition
    arc_connector: str = ""  # Text connecting this to previous item
    role_description: str = ""  # What role this item plays in the arc


@dataclass
class ArcPlan:
    """The complete narrative arc for a single ritual."""

    theme: str  # Auto-detected narrative theme
    items: list[ArcItem]
    created_at: str = ""  # ISO 8601


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def topic_overlap(topics_a: list[str], topics_b: list[str]) -> float:
    """Jaccard similarity on lowercased topic lists."""
    set_a = {t.lower() for t in topics_a}
    set_b = {t.lower() for t in topics_b}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# ---------------------------------------------------------------------------
# Graph-level modifiers
# ---------------------------------------------------------------------------


def apply_modifiers(candidates: list[CandidateItem]) -> list[CandidateItem]:
    """Apply graph-level scoring modifiers to candidate items.

    Modifiers are *additive* — they adjust composite_score without replacing
    the original value.

    Returns the same list with mutated composite_score values.
    """
    if not candidates:
        return candidates

    # --- Narrative tension bonus (+0.5) ---
    for item in candidates:
        for other in candidates:
            if item is other:
                continue
            cats_overlap = bool(
                set(c.lower() for c in item.categories)
                & set(c.lower() for c in other.categories)
            )
            if cats_overlap and item.uniqueness_score > 7:
                item.composite_score += 0.5
                break  # apply at most once per item

    # --- Cross-domain bonus (+0.3) ---
    for item in candidates:
        unique_cats = {c.lower() for c in item.categories}
        if len(unique_cats) >= 2:
            item.composite_score += 0.3

    # --- Redundancy penalty (-1.0) ---
    for i, a in enumerate(candidates):
        for j, b in enumerate(candidates):
            if j <= i:
                continue
            if topic_overlap(a.topics, b.topics) > 0.7:
                if a.composite_score >= b.composite_score:
                    b.composite_score -= 1.0
                else:
                    a.composite_score -= 1.0

    # --- Source diversity penalty (-0.5) ---
    source_counts: Counter[str] = Counter()
    # Sort by composite_score desc so higher-scoring items claim slots first
    for item in sorted(candidates, key=lambda c: c.composite_score, reverse=True):
        src = item.source.lower().strip()
        if src:
            source_counts[src] += 1
            if source_counts[src] >= 3:
                item.composite_score -= 0.5

    # --- Echo bonus (+1.0) ---
    for item in candidates:
        if item.is_echo:
            item.composite_score += 1.0

    # --- Archive freshness bonus (+0.2) — placeholder, always applies ---
    for item in candidates:
        item.composite_score += 0.2

    return candidates


# ---------------------------------------------------------------------------
# Connector / role templates
# ---------------------------------------------------------------------------

_CONNECTORS: dict[ArcPosition, str] = {
    ArcPosition.OPENING: "",
    ArcPosition.DEEP_DIVE: "Going deeper on this thread...",
    ArcPosition.SURPRISE: "Now for something unexpected — ",
    ArcPosition.CONTRARIAN: "But not everyone agrees — ",
    ArcPosition.SYNTHESIS: "Tying it all together — ",
}

_ROLES: dict[ArcPosition, str] = {
    ArcPosition.OPENING: "Sets today's context",
    ArcPosition.DEEP_DIVE: "The core intellectual payload",
    ArcPosition.SURPRISE: "An unexpected connection",
    ArcPosition.CONTRARIAN: "Challenges the dominant narrative",
    ArcPosition.SYNTHESIS: "Connects the threads",
}


# ---------------------------------------------------------------------------
# NarrativeArc
# ---------------------------------------------------------------------------


class NarrativeArc:
    """Builds a narrative arc from scored candidate items."""

    def __init__(
        self, candidates: list[CandidateItem], items_per_ritual: int = 5
    ) -> None:
        self.candidates = candidates
        self.items_per_ritual = items_per_ritual

    def build(self) -> ArcPlan:
        """Main entry point: apply modifiers, select top N, assign positions, generate connectors."""
        self.candidates = apply_modifiers(self.candidates)
        selected = self._select_top()
        arc_items = self._assign_positions(selected)
        arc_items = self._generate_connectors(arc_items)
        theme = self._detect_theme(arc_items)
        return ArcPlan(
            theme=theme,
            items=arc_items,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _select_top(self) -> list[CandidateItem]:
        """Select top items_per_ritual candidates by modified composite_score."""
        ranked = sorted(self.candidates, key=lambda c: c.composite_score, reverse=True)
        return ranked[: self.items_per_ritual]

    def _assign_positions(self, selected: list[CandidateItem]) -> list[ArcItem]:
        """Assign each item to a narrative position.

        Algorithm:
        1. Sort by composite_score desc.
        2. Echo item → OPENING.
        3. Highest depth + insight_density → DEEP_DIVE.
        4. Serendipity (or highest cross-domain) → SURPRISE.
        5. Highest uniqueness → CONTRARIAN.
        6. Most topic overlap with others → SYNTHESIS.
        7. Remaining items fill remaining positions by score.
        8. Fewer items than positions → partial arc.
        """
        if not selected:
            return []

        pool = list(selected)
        assigned: dict[ArcPosition, CandidateItem] = {}
        position_order = list(ArcPosition)

        def _pop(item: CandidateItem) -> None:
            if item in pool:
                pool.remove(item)

        # 1. Echo → OPENING
        echo_items = [c for c in pool if c.is_echo]
        if echo_items:
            best_echo = max(echo_items, key=lambda c: c.composite_score)
            assigned[ArcPosition.OPENING] = best_echo
            _pop(best_echo)

        # 2. Highest depth + insight_density → DEEP_DIVE
        if pool and ArcPosition.DEEP_DIVE not in assigned:
            best_deep = max(pool, key=lambda c: c.depth_score + c.insight_density_score)
            assigned[ArcPosition.DEEP_DIVE] = best_deep
            _pop(best_deep)

        # 3. Serendipity → SURPRISE
        if pool and ArcPosition.SURPRISE not in assigned:
            seren = [c for c in pool if c.is_serendipity]
            if seren:
                best_seren = max(seren, key=lambda c: c.composite_score)
            else:
                # Highest cross-domain: most categories
                best_seren = max(pool, key=lambda c: len(set(c.categories)))
            assigned[ArcPosition.SURPRISE] = best_seren
            _pop(best_seren)

        # 4. Highest uniqueness → CONTRARIAN
        if pool and ArcPosition.CONTRARIAN not in assigned:
            best_contra = max(pool, key=lambda c: c.uniqueness_score)
            assigned[ArcPosition.CONTRARIAN] = best_contra
            _pop(best_contra)

        # 5. Most topic overlap with all other assigned items → SYNTHESIS
        if pool and ArcPosition.SYNTHESIS not in assigned:

            def _total_overlap(candidate: CandidateItem) -> float:
                return sum(
                    topic_overlap(candidate.topics, other.topics)
                    for other in assigned.values()
                )

            best_synth = max(pool, key=_total_overlap)
            assigned[ArcPosition.SYNTHESIS] = best_synth
            _pop(best_synth)

        # 6. Fill OPENING if not yet assigned (no echo)
        if pool and ArcPosition.OPENING not in assigned:
            best_open = max(pool, key=lambda c: c.relevance_score)
            assigned[ArcPosition.OPENING] = best_open
            _pop(best_open)

        # 7. Remaining items → remaining positions by score
        remaining_positions = [p for p in position_order if p not in assigned]
        pool_sorted = sorted(pool, key=lambda c: c.composite_score, reverse=True)
        for pos, item in zip(remaining_positions, pool_sorted):
            assigned[pos] = item

        # Build ordered list
        arc_items: list[ArcItem] = []
        for pos in position_order:
            if pos in assigned:
                arc_items.append(
                    ArcItem(
                        candidate=assigned[pos],
                        position=pos,
                    )
                )
        return arc_items

    def _detect_theme(self, items: list[ArcItem]) -> str:
        """Auto-detect a narrative theme from the items' topics.

        Uses simple frequency counting — the most common topic becomes the
        theme seed.
        """
        if not items:
            return "Curated Discoveries"
        topic_freq: Counter[str] = Counter()
        for ai in items:
            for t in ai.candidate.topics:
                topic_freq[t.lower()] += 1
        if not topic_freq:
            return "Curated Discoveries"
        top_topic = topic_freq.most_common(1)[0][0]
        return top_topic.title()

    def _generate_connectors(self, items: list[ArcItem]) -> list[ArcItem]:
        """Generate arc_connector and role_description for each item based on position."""
        for ai in items:
            ai.arc_connector = _CONNECTORS.get(ai.position, "")
            ai.role_description = _ROLES.get(ai.position, "")
        return items


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_preview(arc_plan: ArcPlan) -> str:
    """Format the ritual preview matching SKILL_v2.md §11.

    Example output:
        📋 Ritual Preview — 5 items planned

        Arc: "Artificial Intelligence"

        1. [Opening] "GPT-5 Announcement" (8.3)
           💭 High relevance to current events
    """
    n = len(arc_plan.items)
    lines: list[str] = [
        f"📋 Ritual Preview — {n} items planned",
        "",
        f'Arc: "{arc_plan.theme}"',
        "",
    ]
    for idx, ai in enumerate(arc_plan.items, 1):
        c = ai.candidate
        lines.append(
            f'{idx}. [{ai.position.label}] "{c.title}" ({c.composite_score:.1f})'
        )
        if c.curation_reason:
            lines.append(f"   💭 {c.curation_reason}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _candidate_from_dict(d: dict) -> CandidateItem:
    """Create a CandidateItem from a plain dict, tolerating missing keys."""
    return CandidateItem(
        title=d.get("title", "Untitled"),
        url=d.get("url", ""),
        composite_score=float(d.get("composite_score", 0.0)),
        relevance_score=float(d.get("relevance_score", 0.0)),
        depth_score=float(d.get("depth_score", 0.0)),
        insight_density_score=float(d.get("insight_density_score", 0.0)),
        uniqueness_score=float(d.get("uniqueness_score", 0.0)),
        categories=d.get("categories", []),
        topics=d.get("topics", []),
        source=d.get("source", ""),
        is_serendipity=bool(d.get("is_serendipity", False)),
        is_echo=bool(d.get("is_echo", False)),
        curation_reason=d.get("curation_reason", ""),
    )


def _arc_plan_to_dict(plan: ArcPlan) -> dict:
    """Serialise an ArcPlan to a JSON-safe dict."""
    return {
        "theme": plan.theme,
        "created_at": plan.created_at,
        "items": [
            {
                "position": ai.position.label,
                "arc_connector": ai.arc_connector,
                "role_description": ai.role_description,
                "title": ai.candidate.title,
                "url": ai.candidate.url,
                "composite_score": ai.candidate.composite_score,
                "curation_reason": ai.candidate.curation_reason,
                "topics": ai.candidate.topics,
                "categories": ai.candidate.categories,
                "source": ai.candidate.source,
            }
            for ai in plan.items
        ],
    }


def arc_from_json(payload_json: str) -> ArcPlan:
    """Parse a JSON array of item dicts, build and return an ArcPlan."""
    raw = json.loads(payload_json)
    if not isinstance(raw, list):
        raise ValueError("Payload must be a JSON array of item dicts")
    candidates = [_candidate_from_dict(d) for d in raw]
    arc = NarrativeArc(candidates)
    return arc.build()


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------


def _run_tests() -> None:
    """Run self-tests and report results."""
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

    def _make_items(n: int = 5) -> list[CandidateItem]:
        """Generate n distinct candidate items for testing."""
        base = [
            CandidateItem(
                title="GPT-5 Announcement",
                composite_score=8.0,
                relevance_score=9.0,
                depth_score=7.0,
                insight_density_score=6.0,
                uniqueness_score=5.0,
                categories=["ai"],
                topics=["gpt", "openai", "language-models"],
                source="techcrunch",
                curation_reason="Major AI milestone",
            ),
            CandidateItem(
                title="Quantum Computing Breakthrough",
                composite_score=7.5,
                relevance_score=6.0,
                depth_score=9.0,
                insight_density_score=8.5,
                uniqueness_score=6.0,
                categories=["physics", "computing"],
                topics=["quantum", "qubits", "computing"],
                source="nature",
                curation_reason="Deep technical analysis",
            ),
            CandidateItem(
                title="Art Meets Algorithms",
                composite_score=6.0,
                relevance_score=4.0,
                depth_score=5.0,
                insight_density_score=5.0,
                uniqueness_score=7.0,
                categories=["art", "technology"],
                topics=["generative-art", "creativity", "algorithms"],
                source="wired",
                is_serendipity=True,
                curation_reason="Unexpected cross-domain connection",
            ),
            CandidateItem(
                title="AI Regulation Backlash",
                composite_score=7.0,
                relevance_score=7.0,
                depth_score=6.0,
                insight_density_score=5.0,
                uniqueness_score=8.5,
                categories=["ai", "policy"],
                topics=["regulation", "ai", "policy"],
                source="reuters",
                curation_reason="Contrarian perspective",
            ),
            CandidateItem(
                title="The Convergence of Bio and Tech",
                composite_score=6.5,
                relevance_score=5.0,
                depth_score=6.0,
                insight_density_score=6.0,
                uniqueness_score=4.0,
                categories=["biology", "technology"],
                topics=["biotech", "ai", "computing", "gpt"],
                source="mit-review",
                curation_reason="Bridges multiple threads",
            ),
        ]
        return [
            CandidateItem(
                title=base[i % len(base)].title,
                composite_score=base[i % len(base)].composite_score,
                relevance_score=base[i % len(base)].relevance_score,
                depth_score=base[i % len(base)].depth_score,
                insight_density_score=base[i % len(base)].insight_density_score,
                uniqueness_score=base[i % len(base)].uniqueness_score,
                categories=list(base[i % len(base)].categories),
                topics=list(base[i % len(base)].topics),
                source=base[i % len(base)].source,
                is_serendipity=base[i % len(base)].is_serendipity,
                is_echo=base[i % len(base)].is_echo,
                curation_reason=base[i % len(base)].curation_reason,
            )
            for i in range(n)
        ]

    print("🧪 Running narrative_arc self-tests...\n")

    # Test 1: 5 items → all 5 positions assigned
    print("  Test: 5 items → all 5 positions assigned")
    items5 = _make_items(5)
    arc = NarrativeArc(items5)
    plan = arc.build()
    positions_assigned = {ai.position for ai in plan.items}
    _assert(len(plan.items) == 5, "5 arc items produced")
    _assert(positions_assigned == set(ArcPosition), "all 5 positions assigned")

    # Test 2: serendipity item → SURPRISE
    print("  Test: serendipity item → SURPRISE")
    items_s = _make_items(5)
    # Ensure only one serendipity
    for c in items_s:
        c.is_serendipity = False
    items_s[2].is_serendipity = True
    items_s[2].title = "Serendipity Special"
    arc_s = NarrativeArc(items_s)
    plan_s = arc_s.build()
    surprise_item = [ai for ai in plan_s.items if ai.position == ArcPosition.SURPRISE]
    _assert(
        len(surprise_item) == 1
        and surprise_item[0].candidate.title == "Serendipity Special",
        "serendipity item assigned to SURPRISE",
    )

    # Test 3: echo item → OPENING
    print("  Test: echo item → OPENING")
    items_e = _make_items(5)
    for c in items_e:
        c.is_echo = False
    items_e[3].is_echo = True
    items_e[3].title = "Echo Priority"
    arc_e = NarrativeArc(items_e)
    plan_e = arc_e.build()
    opening_item = [ai for ai in plan_e.items if ai.position == ArcPosition.OPENING]
    _assert(
        len(opening_item) == 1 and opening_item[0].candidate.title == "Echo Priority",
        "echo item assigned to OPENING",
    )

    # Test 4: redundancy penalty
    print("  Test: redundancy penalty lowers overlapping item score")
    dup_a = CandidateItem(
        title="A",
        composite_score=5.0,
        topics=["x", "y", "z"],
        categories=["cat"],
    )
    dup_b = CandidateItem(
        title="B",
        composite_score=4.0,
        topics=["x", "y", "z"],
        categories=["cat"],
    )
    apply_modifiers([dup_a, dup_b])
    # B should have been penalised by -1.0 (lower score)
    # Both get +0.2 archive freshness; categories count=1 so no cross-domain
    # A: 5.0 + 0.2 = 5.2; B: 4.0 - 1.0 + 0.2 = 3.2
    _assert(
        dup_b.composite_score < dup_a.composite_score,
        "lower-scoring duplicate penalised",
    )

    # Test 5: partial arc with 3 items
    print("  Test: 3 items → partial arc (3 positions)")
    items3 = _make_items(3)
    arc3 = NarrativeArc(items3)
    plan3 = arc3.build()
    _assert(len(plan3.items) == 3, "3 arc items for 3 candidates")

    # Test 6: topic_overlap function
    print("  Test: topic_overlap correctness")
    _assert(
        topic_overlap(["A", "B", "C"], ["a", "b", "c"]) == 1.0,
        "identical (case-insensitive) → 1.0",
    )
    _assert(topic_overlap([], ["a"]) == 0.0, "empty left → 0.0")
    _assert(topic_overlap(["a"], []) == 0.0, "empty right → 0.0")
    _assert(topic_overlap([], []) == 0.0, "both empty → 0.0")
    # {"a","b"} & {"b","c"} = {"b"}, union = {"a","b","c"} → 1/3
    overlap_val = topic_overlap(["a", "b"], ["b", "c"])
    _assert(
        abs(overlap_val - 1 / 3) < 1e-9,
        f"partial overlap → 1/3 (got {overlap_val:.4f})",
    )

    # Test 7: format_preview produces readable text
    print("  Test: format_preview output")
    items_fp = _make_items(5)
    arc_fp = NarrativeArc(items_fp)
    plan_fp = arc_fp.build()
    preview = format_preview(plan_fp)
    _assert("📋 Ritual Preview" in preview, "preview contains header")
    _assert("Arc:" in preview, "preview contains arc theme")
    _assert("[Opening]" in preview, "preview contains [Opening]")
    _assert("💭" in preview, "preview contains curation reasons")

    # Test 8: empty candidates
    print("  Test: empty candidates → empty arc")
    arc_empty = NarrativeArc([])
    plan_empty = arc_empty.build()
    _assert(len(plan_empty.items) == 0, "empty candidates produce empty arc")
    _assert(plan_empty.theme == "Curated Discoveries", "default theme for empty arc")

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
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="The ONLY — Narrative Arc Engine",
    )
    parser.add_argument(
        "--action",
        choices=["build", "preview", "test"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--payload",
        type=str,
        default="",
        help="JSON array of candidate items",
    )
    args = parser.parse_args()

    if args.action == "test":
        _run_tests()
        return

    if args.action in ("build", "preview"):
        if not args.payload:
            print("❌ --payload is required for build/preview", file=sys.stderr)
            sys.exit(1)
        try:
            plan = arc_from_json(args.payload)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Invalid payload: {e}", file=sys.stderr)
            sys.exit(1)

        if args.action == "build":
            print(json.dumps(_arc_plan_to_dict(plan), indent=2, ensure_ascii=False))
        else:
            print(format_preview(plan))
        return


if __name__ == "__main__":
    main()
