#!/usr/bin/env python3
"""
The ONLY — Knowledge Archive
Persistent index of all curated articles across rituals.
Supports search, inter-article linking, monthly summaries,
and HTML cleanup with retention policy.

Actions:
  search  — Search entries by query, topics, date range
  summary — Generate monthly digest
  cleanup — Remove stale HTML files (preserves index metadata)
  status  — Print archive statistics
  test    — Run self-tests
"""

from __future__ import annotations

import os
import sys
import argparse
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from optimized_io import load_json, save_json, timestamp

ARCHIVE_DIR = os.path.expanduser("~/memory/the_only_archive")
INDEX_FILE = os.path.join(ARCHIVE_DIR, "index.json")
CANVAS_DIR = os.path.expanduser("~/.openclaw/canvas")
DEFAULT_HTML_RETENTION_DAYS = 14

DEFAULT_INDEX: dict = {
    "version": "2.0",
    "total_articles": 0,
    "entries": [],
}


def generate_id(timestamp: datetime, sequence: int) -> str:
    """Generate an archive entry ID in ``YYYYMMDD_HHMM_NNN`` format."""
    return f"{timestamp.strftime('%Y%m%d_%H%M')}_{sequence:03d}"


def topic_overlap(topics_a: list[str], topics_b: list[str]) -> float:
    """Return Jaccard similarity between two topic lists (case-insensitive)."""
    set_a = {t.lower() for t in topics_a}
    set_b = {t.lower() for t in topics_b}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ArchiveEntry:
    """A single archived article with metadata and linking info."""

    id: str  # format: YYYYMMDD_HHMM_NNN
    title: str
    topics: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    engagement_score: int = 0
    source: str = ""
    synthesis_style: str = ""
    arc_position: str = ""
    ritual_id: str = ""
    related_articles: list[str] = field(default_factory=list)
    html_path: str = ""
    delivered_at: str = ""  # ISO 8601

    @classmethod
    def from_dict(cls, data: dict) -> ArchiveEntry:
        """Construct an ArchiveEntry from a plain dict."""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            topics=list(data.get("topics", [])),
            quality_score=float(data.get("quality_score", 0.0)),
            engagement_score=int(data.get("engagement_score", 0)),
            source=data.get("source", ""),
            synthesis_style=data.get("synthesis_style", ""),
            arc_position=data.get("arc_position", ""),
            ritual_id=data.get("ritual_id", ""),
            related_articles=list(data.get("related_articles", [])),
            html_path=data.get("html_path", ""),
            delivered_at=data.get("delivered_at", ""),
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON output."""
        return {
            "id": self.id,
            "title": self.title,
            "topics": self.topics,
            "quality_score": self.quality_score,
            "engagement_score": self.engagement_score,
            "source": self.source,
            "synthesis_style": self.synthesis_style,
            "arc_position": self.arc_position,
            "ritual_id": self.ritual_id,
            "related_articles": self.related_articles,
            "html_path": self.html_path,
            "delivered_at": self.delivered_at,
        }


# ---------------------------------------------------------------------------
# KnowledgeArchive
# ---------------------------------------------------------------------------


class KnowledgeArchive:
    """Persistent knowledge archive with search, linking, and cleanup."""

    def __init__(self, archive_dir: str | None = None) -> None:
        """Load index from *archive_dir*/index.json. Create if not exists."""
        self._archive_dir: str = archive_dir or ARCHIVE_DIR
        self._index_file: str = os.path.join(self._archive_dir, "index.json")
        self._index: dict = self._load_index()
        self._entries: list[ArchiveEntry] = [
            ArchiveEntry.from_dict(e) for e in self._index.get("entries", [])
        ]

    # -- persistence --------------------------------------------------------

    def _load_index(self) -> dict:
        """Load the master index, returning DEFAULT_INDEX on first run."""
        return load_json(self._index_file, dict(DEFAULT_INDEX))

    def _save_index(self) -> None:
        """Persist index to disk, syncing total_articles before write."""
        self._index["entries"] = [e.to_dict() for e in self._entries]
        self._index["total_articles"] = len(self._entries)
        save_json(self._index_file, self._index)

    # -- CRUD ---------------------------------------------------------------

    def append(self, entries: list[ArchiveEntry]) -> None:
        """Add new entries to the index and write ritual metadata files.

        Duplicate IDs are silently skipped.  Updates ``total_articles``
        and persists the index after appending.
        """
        existing_ids = {e.id for e in self._entries}
        added: list[ArchiveEntry] = []
        for entry in entries:
            if entry.id not in existing_ids:
                self._entries.append(entry)
                existing_ids.add(entry.id)
                added.append(entry)

        if added:
            rituals: dict[str, list[ArchiveEntry]] = {}
            for entry in added:
                rid = entry.ritual_id or entry.id.rsplit("_", 1)[0]
                rituals.setdefault(rid, []).append(entry)
            for ritual_id, ritual_entries in rituals.items():
                self._create_ritual_metadata(ritual_id, ritual_entries)
            self._save_index()

    def get(self, entry_id: str) -> ArchiveEntry | None:
        """Get a single entry by ID, or ``None`` if not found."""
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def search(
        self,
        query: str | None = None,
        topics: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[ArchiveEntry]:
        """Search entries by text query, topics, and/or date range.

        All filters are AND-combined.  Text matching is case-insensitive
        against title and topics.  Returns results sorted by
        ``delivered_at`` descending.
        """
        results = list(self._entries)

        if query:
            q = query.lower()
            results = [
                e
                for e in results
                if q in e.title.lower() or any(q in t.lower() for t in e.topics)
            ]

        if topics:
            topic_set = {t.lower() for t in topics}
            results = [e for e in results if topic_set & {t.lower() for t in e.topics}]

        if date_from:
            results = [e for e in results if e.delivered_at >= date_from]

        if date_to:
            results = [e for e in results if e.delivered_at <= date_to]

        results.sort(key=lambda e: e.delivered_at, reverse=True)
        return results

    # -- linking ------------------------------------------------------------

    def link(self, id_a: str, id_b: str) -> None:
        """Create a bidirectional related_articles link between two entries."""
        entry_a = self.get(id_a)
        entry_b = self.get(id_b)
        if entry_a is None or entry_b is None:
            return
        if id_b not in entry_a.related_articles:
            entry_a.related_articles.append(id_b)
        if id_a not in entry_b.related_articles:
            entry_b.related_articles.append(id_a)
        self._save_index()

    def auto_link(self, new_entries: list[ArchiveEntry]) -> int:
        """Scan all existing entries for topic overlap > 0.5 with *new_entries*.

        Creates bidirectional links.  Returns count of new links created.
        """
        new_links = 0
        for new_entry in new_entries:
            for existing in self._entries:
                if existing.id == new_entry.id:
                    continue
                if topic_overlap(new_entry.topics, existing.topics) > 0.5:
                    added = False
                    if existing.id not in new_entry.related_articles:
                        new_entry.related_articles.append(existing.id)
                        added = True
                    if new_entry.id not in existing.related_articles:
                        existing.related_articles.append(new_entry.id)
                        added = True
                    if added:
                        new_links += 1
        if new_links:
            self._save_index()
        return new_links

    # -- analytics ----------------------------------------------------------

    def monthly_summary(self, year: int, month: int) -> dict:
        """Generate a digest for the given month.

        Returns a dict with keys: ``total_articles``, ``top_topics``,
        ``avg_quality``, ``avg_engagement``, ``top_engagement``,
        ``sources``, ``arc_positions``.
        """
        prefix = f"{year:04d}-{month:02d}"
        month_entries = [e for e in self._entries if e.delivered_at.startswith(prefix)]

        total = len(month_entries)

        topic_counter: Counter[str] = Counter()
        for e in month_entries:
            for t in e.topics:
                topic_counter[t.lower()] += 1
        top_topics = topic_counter.most_common(10)

        avg_quality = (
            sum(e.quality_score for e in month_entries) / total if total else 0.0
        )
        avg_engagement = (
            sum(e.engagement_score for e in month_entries) / total if total else 0.0
        )

        by_engagement = sorted(
            month_entries, key=lambda e: e.engagement_score, reverse=True
        )
        top_engagement = [
            {"id": e.id, "title": e.title, "engagement_score": e.engagement_score}
            for e in by_engagement[:5]
        ]

        source_counter: Counter[str] = Counter()
        for e in month_entries:
            source_counter[e.source or "unknown"] += 1

        arc_counter: Counter[str] = Counter()
        for e in month_entries:
            arc_counter[e.arc_position or "unassigned"] += 1

        return {
            "total_articles": total,
            "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
            "avg_quality": round(avg_quality, 2),
            "avg_engagement": round(avg_engagement, 2),
            "top_engagement": top_engagement,
            "sources": dict(source_counter),
            "arc_positions": dict(arc_counter),
        }

    # -- cleanup ------------------------------------------------------------

    def cleanup_html(
        self,
        days: int = DEFAULT_HTML_RETENTION_DAYS,
        canvas_dir: str | None = None,
    ) -> int:
        """Remove HTML files older than *days* from *canvas_dir*.

        Archive metadata in the index is **never** deleted.
        Returns count of files removed.
        """
        cdir = canvas_dir or CANVAS_DIR
        if not os.path.exists(cdir):
            return 0
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        for fname in os.listdir(cdir):
            if not fname.startswith("the_only_") or not fname.endswith(".html"):
                continue
            fpath = os.path.join(cdir, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)
                    removed += 1
            except OSError:
                continue
        return removed

    # -- stats --------------------------------------------------------------

    def total_count(self) -> int:
        """Return total article count."""
        return len(self._entries)

    # -- internal -----------------------------------------------------------

    def _create_ritual_metadata(
        self, ritual_id: str, entries: list[ArchiveEntry]
    ) -> None:
        """Write ritual metadata into a date-based subdirectory.

        Path: ``archive_dir/YYYY/MM/ritual_id.json``
        """
        try:
            year = ritual_id[:4]
            month = ritual_id[4:6]
        except (IndexError, ValueError):
            return

        subdir = os.path.join(self._archive_dir, year, month)
        os.makedirs(subdir, exist_ok=True)

        metadata = {
            "ritual_id": ritual_id,
            "article_count": len(entries),
            "articles": [e.to_dict() for e in entries],
            "created_at": datetime.now().isoformat(),
        }
        fpath = os.path.join(subdir, f"{ritual_id}.json")
        save_json(fpath, metadata)


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------


def _run_tests() -> None:
    """Execute self-tests using tempfile-backed archive dirs."""
    passed = 0
    failed = 0

    def _assert(condition: bool, label: str) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {label}")
        else:
            failed += 1
            print(f"  ❌ {label}", file=sys.stderr)

    print("🧪 Knowledge Archive — self-tests\n")

    # Test: generate_id format
    print("  Test: generate_id format")
    ts = datetime(2026, 3, 25, 9, 0)
    gid = generate_id(ts, 1)
    _assert(gid == "20260325_0900_001", f"generate_id → {gid}")
    gid2 = generate_id(ts, 42)
    _assert(gid2 == "20260325_0900_042", f"generate_id seq=42 → {gid2}")

    # Test: topic_overlap
    print("  Test: topic_overlap correctness")
    _assert(
        topic_overlap(["A", "B", "C"], ["a", "b", "c"]) == 1.0,
        "identical (case-insensitive) → 1.0",
    )
    _assert(topic_overlap([], ["a"]) == 0.0, "empty left → 0.0")
    _assert(topic_overlap(["a"], []) == 0.0, "empty right → 0.0")
    _assert(topic_overlap([], []) == 0.0, "both empty → 0.0")
    overlap_val = topic_overlap(["a", "b"], ["b", "c"])
    _assert(
        abs(overlap_val - 1 / 3) < 1e-9,
        f"partial overlap → 1/3 (got {overlap_val:.4f})",
    )

    # Test: append + get round-trip
    print("  Test: append + get round-trip")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        entry = ArchiveEntry(
            id="20260325_0900_001",
            title="Test Article",
            topics=["ai", "ml"],
            quality_score=7.5,
            engagement_score=3,
            source="arxiv",
            ritual_id="20260325_0900",
            delivered_at="2026-03-25T09:00:00Z",
        )
        archive.append([entry])
        got = archive.get("20260325_0900_001")
        _assert(got is not None, "get returns appended entry")
        assert got is not None
        _assert(got.title == "Test Article", "title preserved")
        _assert(got.quality_score == 7.5, "quality_score preserved")

        archive2 = KnowledgeArchive(archive_dir=tmpdir)
        _assert(archive2.total_count() == 1, "index persisted to disk")

        ritual_file = os.path.join(tmpdir, "2026", "03", "20260325_0900.json")
        _assert(os.path.exists(ritual_file), "ritual metadata file created")

    # Test: search by query (case-insensitive title match)
    print("  Test: search by query")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        entries = [
            ArchiveEntry(
                id="20260325_0900_001",
                title="How Transformers Scale",
                topics=["ai", "transformers"],
                delivered_at="2026-03-25T09:00:00Z",
            ),
            ArchiveEntry(
                id="20260325_0900_002",
                title="Rust Memory Safety",
                topics=["rust", "systems"],
                delivered_at="2026-03-25T09:05:00Z",
            ),
        ]
        archive.append(entries)
        results = archive.search(query="transformers")
        _assert(len(results) == 1, "query matches one entry")
        _assert(results[0].id == "20260325_0900_001", "correct entry matched")

        results_ci = archive.search(query="RUST")
        _assert(len(results_ci) == 1, "case-insensitive query match")

    # Test: search by topics (intersection)
    print("  Test: search by topics")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        entries = [
            ArchiveEntry(
                id="20260325_0900_001",
                title="Article A",
                topics=["ai", "ml"],
                delivered_at="2026-03-25T09:00:00Z",
            ),
            ArchiveEntry(
                id="20260325_0900_002",
                title="Article B",
                topics=["rust", "systems"],
                delivered_at="2026-03-25T09:05:00Z",
            ),
            ArchiveEntry(
                id="20260325_0900_003",
                title="Article C",
                topics=["ai", "robotics"],
                delivered_at="2026-03-25T09:10:00Z",
            ),
        ]
        archive.append(entries)
        results = archive.search(topics=["ai"])
        _assert(len(results) == 2, "topic filter matches two entries")
        ids = {r.id for r in results}
        _assert(
            "20260325_0900_001" in ids and "20260325_0900_003" in ids,
            "correct entries matched by topic",
        )

    # Test: search by date range
    print("  Test: search by date range")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        entries = [
            ArchiveEntry(
                id="20260320_0900_001",
                title="Old Article",
                delivered_at="2026-03-20T09:00:00Z",
            ),
            ArchiveEntry(
                id="20260325_0900_001",
                title="New Article",
                delivered_at="2026-03-25T09:00:00Z",
            ),
        ]
        archive.append(entries)
        results = archive.search(date_from="2026-03-24")
        _assert(len(results) == 1, "date_from filter works")
        _assert(results[0].id == "20260325_0900_001", "correct entry by date_from")

        results2 = archive.search(date_to="2026-03-21")
        _assert(len(results2) == 1, "date_to filter works")
        _assert(results2[0].id == "20260320_0900_001", "correct entry by date_to")

    # Test: link bidirectionality
    print("  Test: link bidirectionality")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        entries = [
            ArchiveEntry(
                id="20260325_0900_001",
                title="A",
                delivered_at="2026-03-25T09:00:00Z",
            ),
            ArchiveEntry(
                id="20260325_0900_002",
                title="B",
                delivered_at="2026-03-25T09:05:00Z",
            ),
        ]
        archive.append(entries)
        archive.link("20260325_0900_001", "20260325_0900_002")
        a = archive.get("20260325_0900_001")
        b = archive.get("20260325_0900_002")
        assert a is not None and b is not None
        _assert(
            "20260325_0900_002" in a.related_articles,
            "A → B link exists",
        )
        _assert(
            "20260325_0900_001" in b.related_articles,
            "B → A link exists",
        )

    # Test: auto_link with overlapping topics
    print("  Test: auto_link")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        e1 = ArchiveEntry(
            id="20260325_0900_001",
            title="AI Deep Dive",
            topics=["ai", "ml", "transformers"],
            delivered_at="2026-03-25T09:00:00Z",
        )
        archive.append([e1])

        e2 = ArchiveEntry(
            id="20260325_2100_001",
            title="ML Progress",
            topics=["ai", "ml", "transformers", "scaling"],
            delivered_at="2026-03-25T21:00:00Z",
        )
        archive.append([e2])

        new_links = archive.auto_link([e2])
        _assert(new_links > 0, f"auto_link created {new_links} link(s)")
        got1 = archive.get("20260325_0900_001")
        got2 = archive.get("20260325_2100_001")
        assert got1 is not None and got2 is not None
        _assert(
            "20260325_2100_001" in got1.related_articles,
            "auto_link: e1 → e2",
        )
        _assert(
            "20260325_0900_001" in got2.related_articles,
            "auto_link: e2 → e1",
        )

    # Test: monthly_summary
    print("  Test: monthly_summary")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        entries = [
            ArchiveEntry(
                id="20260325_0900_001",
                title="Article 1",
                topics=["ai", "ml"],
                quality_score=8.0,
                engagement_score=5,
                source="arxiv",
                arc_position="deep_dive",
                delivered_at="2026-03-25T09:00:00Z",
            ),
            ArchiveEntry(
                id="20260325_0900_002",
                title="Article 2",
                topics=["ai", "robotics"],
                quality_score=7.0,
                engagement_score=3,
                source="blog",
                arc_position="opening",
                delivered_at="2026-03-25T09:05:00Z",
            ),
            ArchiveEntry(
                id="20260225_0900_001",
                title="Feb Article",
                topics=["rust"],
                quality_score=9.0,
                engagement_score=10,
                source="blog",
                delivered_at="2026-02-25T09:00:00Z",
            ),
        ]
        archive.append(entries)
        summary = archive.monthly_summary(2026, 3)
        _assert(summary["total_articles"] == 2, "summary: correct article count")
        _assert(
            summary["avg_quality"] == 7.5,
            f"summary: avg_quality={summary['avg_quality']}",
        )
        top_topic_names = [t["topic"] for t in summary["top_topics"]]
        _assert("ai" in top_topic_names, "summary: 'ai' in top topics")
        _assert(summary["sources"].get("arxiv") == 1, "summary: source breakdown")

    # Test: total_count
    print("  Test: total_count")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = KnowledgeArchive(archive_dir=tmpdir)
        _assert(archive.total_count() == 0, "empty archive → 0")
        archive.append(
            [
                ArchiveEntry(
                    id="20260325_0900_001",
                    title="X",
                    delivered_at="2026-03-25T09:00:00Z",
                ),
                ArchiveEntry(
                    id="20260325_0900_002",
                    title="Y",
                    delivered_at="2026-03-25T09:05:00Z",
                ),
            ]
        )
        _assert(archive.total_count() == 2, "two entries → 2")

    # Test: cleanup_html
    print("  Test: cleanup_html")
    with tempfile.TemporaryDirectory() as tmpdir:
        canvas = os.path.join(tmpdir, "canvas")
        os.makedirs(canvas)
        old_file = os.path.join(canvas, "the_only_20260301_0900_001.html")
        with open(old_file, "w") as f:
            f.write("<html></html>")
        old_ts = (datetime.now() - timedelta(days=30)).timestamp()
        os.utime(old_file, (old_ts, old_ts))
        new_file = os.path.join(canvas, "the_only_20260325_0900_001.html")
        with open(new_file, "w") as f:
            f.write("<html></html>")
        other_file = os.path.join(canvas, "other.html")
        with open(other_file, "w") as f:
            f.write("<html></html>")

        archive = KnowledgeArchive(archive_dir=tmpdir)
        removed = archive.cleanup_html(days=14, canvas_dir=canvas)
        _assert(removed == 1, f"cleanup removed {removed} file(s)")
        _assert(not os.path.exists(old_file), "old HTML file removed")
        _assert(os.path.exists(new_file), "recent HTML file kept")
        _assert(os.path.exists(other_file), "non-matching file kept")

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
        description="The ONLY — Knowledge Archive",
    )
    parser.add_argument(
        "--action",
        choices=["search", "summary", "cleanup", "status", "test"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--query", type=str, default=None, help="Text search query")
    parser.add_argument(
        "--topics", type=str, default=None, help="Comma-separated topic filter"
    )
    parser.add_argument("--date-from", type=str, default=None, help="Start date filter")
    parser.add_argument("--date-to", type=str, default=None, help="End date filter")
    parser.add_argument("--year", type=int, default=None, help="Year for summary")
    parser.add_argument("--month", type=int, default=None, help="Month for summary")
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_HTML_RETENTION_DAYS,
        help="HTML retention days for cleanup",
    )
    parser.add_argument(
        "--archive-dir",
        type=str,
        default=None,
        help="Override archive directory",
    )
    args = parser.parse_args()

    if args.action == "test":
        _run_tests()
        return

    archive = KnowledgeArchive(archive_dir=args.archive_dir)

    if args.action == "search":
        topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
        results = archive.search(
            query=args.query,
            topics=topics,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        if not results:
            print("📭 No matching entries found.")
        else:
            print(f"📚 Found {len(results)} entries:\n")
            for entry in results:
                topics_str = ", ".join(entry.topics) if entry.topics else "—"
                print(f"  [{entry.id}] {entry.title}")
                print(f"    Topics: {topics_str}  |  Quality: {entry.quality_score}")
                print(f"    Source: {entry.source}  |  Delivered: {entry.delivered_at}")
                if entry.related_articles:
                    print(f"    Related: {', '.join(entry.related_articles)}")
                print()

    elif args.action == "summary":
        if args.year is None or args.month is None:
            print("❌ --year and --month required for summary", file=sys.stderr)
            sys.exit(1)
        summary = archive.monthly_summary(args.year, args.month)
        print(
            f"📊 Monthly Summary — {args.year}-{args.month:02d}\n"
            f"  Articles: {summary['total_articles']}\n"
            f"  Avg Quality: {summary['avg_quality']}\n"
            f"  Avg Engagement: {summary['avg_engagement']}\n"
        )
        if summary["top_topics"]:
            print("  Top Topics:")
            for t in summary["top_topics"]:
                print(f"    • {t['topic']} ({t['count']})")
        if summary["top_engagement"]:
            print("\n  Top Engagement:")
            for a in summary["top_engagement"]:
                print(
                    f"    • [{a['id']}] {a['title']} (score: {a['engagement_score']})"
                )
        if summary["sources"]:
            print("\n  Sources:")
            for src, cnt in summary["sources"].items():
                print(f"    • {src}: {cnt}")
        if summary["arc_positions"]:
            print("\n  Arc Positions:")
            for pos, cnt in summary["arc_positions"].items():
                print(f"    • {pos}: {cnt}")

    elif args.action == "cleanup":
        removed = archive.cleanup_html(days=args.days)
        if removed:
            print(f"🧹 Removed {removed} HTML file(s) older than {args.days} days.")
        else:
            print("✨ No stale HTML files to remove.")

    elif args.action == "status":
        count = archive.total_count()
        print(f"📚 Knowledge Archive Status\n  Total articles: {count}")
        if count > 0:
            entries = archive.search()
            newest = entries[0].delivered_at if entries else "—"
            oldest = entries[-1].delivered_at if entries else "—"
            print(f"  Date range: {oldest} → {newest}")

            topic_counter: Counter[str] = Counter()
            for e in entries:
                for t in e.topics:
                    topic_counter[t.lower()] += 1
            top5 = topic_counter.most_common(5)
            if top5:
                print("  Top topics:")
                for t, c in top5:
                    print(f"    • {t} ({c})")


if __name__ == "__main__":
    main()
