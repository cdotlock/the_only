#!/usr/bin/env python3
"""
The ONLY — Knowledge Archive
Persistent index of all curated articles across rituals.
Supports indexing, search, inter-article linking, monthly summaries,
and HTML cleanup with retention policy.

Actions:
  index   — Add articles to archive and auto-link related entries
  search  — Search entries by query, topics, date range
  summary — Generate monthly digest
  cleanup — Remove stale HTML files (preserves index metadata)
  status  — Print archive statistics
"""

from __future__ import annotations

import os
import sys
import argparse
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import json


def load_json(path, default=None):
    """Load JSON from file, returning default if missing or corrupt."""
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[warn] {path}: {e}", file=sys.stderr)
    return default


def save_json(path, data):
    """Atomically write JSON to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)

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
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="The ONLY — Knowledge Archive",
    )
    parser.add_argument(
        "--action",
        choices=["index", "search", "summary", "cleanup", "status"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="JSON array of article dicts for --action index",
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

    archive = KnowledgeArchive(archive_dir=args.archive_dir)

    if args.action == "index":
        if not args.data:
            print("❌ --data required for index", file=sys.stderr)
            sys.exit(1)
        try:
            raw = json.loads(args.data)
        except json.JSONDecodeError as exc:
            print(f"❌ Invalid JSON: {exc}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(raw, list):
            print("❌ --data must be a JSON array of article objects", file=sys.stderr)
            sys.exit(1)
        entries = [ArchiveEntry.from_dict(item) for item in raw]
        before = archive.total_count()
        archive.append(entries)
        new_links = archive.auto_link(entries)
        after = archive.total_count()
        added = after - before
        print(f"📚 Indexed {added} article(s). {new_links} new link(s) created.")

    elif args.action == "search":
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
