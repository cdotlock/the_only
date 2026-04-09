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

    # -- transparency report ------------------------------------------------

    def transparency_report(self, year: int, month: int) -> dict:
        """Generate a monthly transparency/self-report.

        Shows Ruby's decisions, biases, performance, and invites overrides.
        This is the "glass box" — the user sees exactly how Ruby thinks.
        """
        month_entries = self._entries_for_month(year, month)
        total = len(month_entries)

        if total == 0:
            return {"error": f"No articles found for {year}-{month:02d}"}

        # ── 1. Content Distribution ──
        topic_counter: Counter[str] = Counter()
        source_counter: Counter[str] = Counter()
        arc_counter: Counter[str] = Counter()
        style_counter: Counter[str] = Counter()
        for e in month_entries:
            for t in e.topics:
                topic_counter[t.lower()] += 1
            source_counter[e.source or "unknown"] += 1
            arc_counter[e.arc_position or "unassigned"] += 1
            style_counter[e.synthesis_style or "standard"] += 1

        topic_total = sum(topic_counter.values())
        topic_distribution = {
            t: {"count": c, "pct": round(c / topic_total * 100, 1)}
            for t, c in topic_counter.most_common(10)
        }

        # ── 2. Quality Metrics ──
        quality_scores = [e.quality_score for e in month_entries if e.quality_score > 0]
        engagement_scores = [e.engagement_score for e in month_entries if e.engagement_score > 0]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0

        # Quality trend (first half vs second half of month)
        mid = total // 2
        first_half_q = [e.quality_score for e in month_entries[:mid] if e.quality_score > 0]
        second_half_q = [e.quality_score for e in month_entries[mid:] if e.quality_score > 0]
        quality_trend = "improving" if (
            second_half_q and first_half_q and
            sum(second_half_q) / len(second_half_q) > sum(first_half_q) / len(first_half_q) + 0.3
        ) else "declining" if (
            second_half_q and first_half_q and
            sum(second_half_q) / len(second_half_q) < sum(first_half_q) / len(first_half_q) - 0.3
        ) else "stable"

        # ── 3. Potential Biases ──
        biases = []
        # Source concentration
        top_source, top_count = source_counter.most_common(1)[0] if source_counter else ("", 0)
        if top_count > total * 0.4:
            biases.append({
                "type": "source_concentration",
                "detail": f"{top_source} provided {top_count}/{total} articles ({top_count/total:.0%})",
                "suggestion": f"Consider diversifying away from {top_source}",
            })
        # Topic echo chamber
        top_topic, top_topic_count = topic_counter.most_common(1)[0] if topic_counter else ("", 0)
        if topic_total > 0 and top_topic_count / topic_total > 0.5:
            biases.append({
                "type": "topic_echo_chamber",
                "detail": f"'{top_topic}' appears in {top_topic_count}/{topic_total} topic slots ({top_topic_count/topic_total:.0%})",
                "suggestion": "Increase serendipity allocation or explore adjacent domains",
            })
        # Low serendipity
        surprise_count = arc_counter.get("surprise", 0) + arc_counter.get("Surprise", 0)
        if total >= 10 and surprise_count < total * 0.1:
            biases.append({
                "type": "low_serendipity",
                "detail": f"Only {surprise_count} surprise items in {total} articles",
                "suggestion": "Raise serendipity floor or widen cross-domain search",
            })

        # ── 4. Best & Worst ──
        by_engagement = sorted(month_entries, key=lambda e: e.engagement_score, reverse=True)
        best = [
            {"id": e.id, "title": e.title, "engagement": e.engagement_score, "quality": e.quality_score}
            for e in by_engagement[:3]
        ]
        worst = [
            {"id": e.id, "title": e.title, "engagement": e.engagement_score, "quality": e.quality_score}
            for e in by_engagement[-3:] if e.engagement_score >= 0
        ]

        # ── 5. Source Reliability ──
        source_quality: dict[str, list[float]] = {}
        for e in month_entries:
            source_quality.setdefault(e.source or "unknown", []).append(e.quality_score)
        source_report = {
            src: {
                "articles": len(scores),
                "avg_quality": round(sum(scores) / len(scores), 2),
            }
            for src, scores in source_quality.items()
        }

        return {
            "period": f"{year}-{month:02d}",
            "total_articles": total,
            "content_distribution": {
                "topics": topic_distribution,
                "sources": dict(source_counter),
                "arc_positions": dict(arc_counter),
                "synthesis_styles": dict(style_counter),
            },
            "quality": {
                "avg_quality": round(avg_quality, 2),
                "avg_engagement": round(avg_engagement, 2),
                "quality_trend": quality_trend,
            },
            "potential_biases": biases,
            "highlights": {
                "best_received": best,
                "least_engaged": worst,
            },
            "source_reliability": source_report,
            "override_prompts": [
                "Adjust topic ratios: tell Ruby 'increase [topic] to [N]%' or 'decrease [topic]'",
                "Exclude a source: 'stop using [source]'",
                "Force serendipity: 'more surprises' or 'set serendipity to [N]%'",
                "Change depth: 'go deeper on [topic]' or 'keep it brief'",
                "Redirect focus: 'I'm done with [topic], focus on [new topic]'",
            ],
        }

    def _entries_for_month(self, year: int, month: int) -> list[ArchiveEntry]:
        """Filter entries to a specific year-month."""
        prefix = f"{year}{month:02d}"
        return [e for e in self._entries if e.id.startswith(prefix)]

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
        choices=["index", "search", "summary", "cleanup", "status", "report"],
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

    elif args.action == "report":
        if args.year is None or args.month is None:
            print("❌ --year and --month required for report", file=sys.stderr)
            sys.exit(1)
        report = archive.transparency_report(args.year, args.month)
        if "error" in report:
            print(f"📭 {report['error']}")
        else:
            print(f"═══ Ruby Transparency Report — {report['period']} ═══\n")
            print(f"📊 Total articles delivered: {report['total_articles']}")

            q = report["quality"]
            print(f"\n📈 Quality: avg {q['avg_quality']} | Engagement: avg {q['avg_engagement']} | Trend: {q['quality_trend']}")

            dist = report["content_distribution"]
            print("\n📋 Topic Distribution:")
            for topic, info in dist["topics"].items():
                print(f"    • {topic}: {info['count']} ({info['pct']}%)")

            print(f"\n📡 Sources: {dist['sources']}")
            print(f"📐 Arc positions: {dist['arc_positions']}")

            if report["potential_biases"]:
                print("\n⚠️  Potential Biases Detected:")
                for bias in report["potential_biases"]:
                    print(f"    • [{bias['type']}] {bias['detail']}")
                    print(f"      → {bias['suggestion']}")

            hl = report["highlights"]
            if hl["best_received"]:
                print("\n🌟 Best Received:")
                for a in hl["best_received"]:
                    print(f"    • {a['title']} (engagement: {a['engagement']}, quality: {a['quality']})")
            if hl["least_engaged"]:
                print("\n📉 Least Engaged:")
                for a in hl["least_engaged"]:
                    print(f"    • {a['title']} (engagement: {a['engagement']}, quality: {a['quality']})")

            print(f"\n📡 Source Reliability:")
            for src, info in report["source_reliability"].items():
                print(f"    • {src}: {info['articles']} articles, avg quality {info['avg_quality']}")

            print("\n🎛️  Override Options:")
            for prompt in report["override_prompts"]:
                print(f"    • {prompt}")

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
