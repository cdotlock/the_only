#!/usr/bin/env python3
"""
Test Data Generator for the_only V2
─────────────────────────────────────
Generates deterministic test data for end-to-end testing.
Uses a fixed seed for reproducibility.

Usage:
    from tests.data_generator import TestDataGenerator
    generator = TestDataGenerator(seed=42)
    articles = generator.generate_articles(count=20)
"""

from __future__ import annotations

import json
import os
import random
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class TestDataGenerator:
    """Generates deterministic test data for the_only V2."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.base_time = datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc)

    def generate_articles(self, count: int = 20) -> list[dict]:
        """Generate deterministic test articles."""
        articles = []
        topics_pool = [
            "ai",
            "machine_learning",
            "deep_learning",
            "llm",
            "transformers",
            "distributed_systems",
            "rust",
            "python",
            "blockchain",
            "quantum_computing",
            "bioinformatics",
            "climate_science",
            "robotics",
            "computer_vision",
            "nlp",
        ]

        for i in range(count):
            topic_idx = (i * 3 + self.seed) % len(topics_pool)
            topic = topics_pool[topic_idx]

            article = {
                "title": f"Test Article {i + 1}: {topic.replace('_', ' ').title()} Deep Dive",
                "url": f"https://example.com/articles/{self.seed}/{i + 1}",
                "content": f"This is a comprehensive analysis of {topic.replace('_', ' ')}. "
                * 10,
                "source": ["arxiv", "hackernews", "blog", "research"][i % 4],
                "topics": [topic, topics_pool[(topic_idx + 1) % len(topics_pool)]],
                "quality_score": 5.0 + (i % 5),
                "relevance_score": 0.5 + (i % 5) * 0.1,
                "freshness_score": 0.8 - (i % 10) * 0.05,
                "depth_score": 0.7 + (i % 3) * 0.1,
                "uniqueness_score": 0.6 + (i % 4) * 0.1,
                "actionability_score": 0.5 + (i % 5) * 0.1,
                "composite_score": 6.0 + (i % 4),
                "curation_reason": f"Selected for {topic} expertise",
                "is_serendipity": i % 7 == 0,
                "is_echo": i % 11 == 0,
                "from_mesh": i % 13 == 0,
            }
            articles.append(article)

        return articles

    def generate_memory_snapshot(self) -> dict:
        """Generate a test memory snapshot."""
        return {
            "core": {
                "version": "2.0",
                "identity": {
                    "current_focus": ["ai", "distributed_systems", "rust"],
                    "professional_domain": "software_engineering",
                    "knowledge_level": {
                        "ai": "advanced",
                        "rust": "intermediate",
                        "distributed_systems": "advanced",
                    },
                    "values": ["depth", "novelty", "actionability"],
                    "anti_interests": ["celebrity_gossip", "sports"],
                },
                "reading_preferences": {
                    "preferred_length": "long-form",
                    "preferred_style": "deep analysis",
                    "emotional_vibe": "intellectually curious",
                },
                "established_at": self.base_time.isoformat(),
                "last_validated": (self.base_time + timedelta(days=7)).isoformat(),
            },
            "semantic": {
                "version": "2.0",
                "last_compressed": (self.base_time + timedelta(days=5)).isoformat(),
                "fetch_strategy": {
                    "primary_sources": ["arxiv", "hackernews", "semanticscholar"],
                    "exclusions": ["sports", "celebrity"],
                    "ratio": {
                        "tech": 50,
                        "serendipity": 20,
                        "research": 20,
                        "philosophy": 10,
                    },
                    "synthesis_rules": [
                        "Always connect to existing knowledge",
                        "Prioritize depth over breadth",
                        "Include contrarian perspectives",
                    ],
                    "tool_preferences": "web_search for breadth, read_url for depth",
                },
                "source_intelligence": {
                    "arxiv": {
                        "quality_avg": 8.5,
                        "quality_scores": [8.0, 8.5, 9.0, 8.5, 8.0],
                        "reliability": 0.95,
                        "consecutive_failures": 0,
                        "depth": "high",
                        "bias": "academic",
                        "freshness": "daily",
                        "exclusivity": 0.8,
                        "best_for": "cutting-edge research",
                        "redundancy_with": {"semanticscholar": 0.3},
                        "last_evaluated": self.base_time.isoformat(),
                    },
                    "hackernews": {
                        "quality_avg": 7.2,
                        "quality_scores": [7.0, 7.5, 7.0, 7.5, 7.0],
                        "reliability": 0.90,
                        "consecutive_failures": 0,
                        "depth": "medium",
                        "bias": "practical",
                        "freshness": "hourly",
                        "exclusivity": 0.6,
                        "best_for": "industry trends",
                        "redundancy_with": {"reddit": 0.4},
                        "last_evaluated": self.base_time.isoformat(),
                    },
                },
                "engagement_patterns": {
                    "ai": {"avg_score": 4.2, "count": 15},
                    "rust": {"avg_score": 3.8, "count": 10},
                    "distributed_systems": {"avg_score": 4.0, "count": 8},
                },
                "temporal_patterns": {
                    "morning_preference": "deep analysis",
                    "evening_preference": "serendipity",
                    "weekday_focus": "technical",
                    "weekend_focus": "broader",
                },
                "synthesis_effectiveness": {
                    "depth_analysis": {"success_rate": 0.85, "avg_engagement": 4.1},
                    "comparison": {"success_rate": 0.75, "avg_engagement": 3.8},
                    "surprise": {"success_rate": 0.70, "avg_engagement": 3.5},
                },
                "emerging_interests": [
                    {
                        "topic": "quantum_computing",
                        "signal_count": 3,
                        "first_seen": self.base_time.isoformat(),
                        "status": "monitoring",
                    },
                    {
                        "topic": "bioinformatics",
                        "signal_count": 2,
                        "first_seen": (self.base_time + timedelta(days=2)).isoformat(),
                        "status": "monitoring",
                    },
                ],
                "evolution_log": [
                    {
                        "timestamp": self.base_time.isoformat(),
                        "description": "Initial setup",
                    },
                    {
                        "timestamp": (self.base_time + timedelta(days=3)).isoformat(),
                        "description": "Added rust to focus areas",
                    },
                ],
            },
            "episodic": {
                "version": "2.0",
                "entries": self._generate_episodic_entries(50),
            },
        }

    def _generate_episodic_entries(self, count: int) -> list[dict]:
        """Generate test episodic entries."""
        entries = []
        for i in range(count):
            entry = {
                "ritual_id": i + 1,
                "timestamp": (self.base_time + timedelta(hours=i)).isoformat(),
                "items_delivered": 5,
                "avg_quality_score": 6.0 + (i % 4),
                "categories": {
                    "ai": 2,
                    "rust": 1,
                    "distributed_systems": 1,
                    "serendipity": 1,
                },
                "engagement": {
                    "item_1": {"score": 4, "signal": "reply", "topic": "ai"},
                    "item_2": {"score": 3, "signal": "reaction", "topic": "rust"},
                    "item_3": {
                        "score": 2,
                        "signal": "viewed",
                        "topic": "distributed_systems",
                    },
                },
                "sources_used": ["arxiv", "hackernews"],
                "sources_failed": [],
                "echo_fulfilled": i % 5 == 0,
                "network_items": 1 if i % 3 == 0 else 0,
                "search_queries": 3,
                "narrative_theme": f"Theme {i % 5}",
                "synthesis_styles": {
                    "deep_analysis": 3,
                    "comparison": 1,
                    "surprise": 1,
                },
                "self_notes": f"Note for ritual {i + 1}",
            }
            entries.append(entry)
        return entries

    def generate_ritual_log(self, count: int = 50) -> list[dict]:
        """Generate test ritual log entries."""
        entries = []
        for i in range(count):
            entry = {
                "ts": int((self.base_time + timedelta(hours=i)).timestamp()),
                "items": 5,
                "network_items": 1 if i % 3 == 0 else 0,
                "categories": {"ai": 2, "rust": 1, "other": 2},
                "avg_quality": 6.0 + (i % 4),
                "echo_fulfilled": i % 5 == 0,
                "styles": {"deep_analysis": 3, "comparison": 1, "surprise": 1},
            }
            entries.append(entry)
        return entries

    def generate_source_profiles(self) -> dict:
        """Generate test source profiles."""
        return {
            "arxiv": {
                "quality_avg": 8.5,
                "quality_scores": [8.0, 8.5, 9.0, 8.5, 8.0],
                "reliability": 0.95,
                "consecutive_failures": 0,
                "depth": "high",
                "bias": "academic",
                "freshness": "daily",
                "exclusivity": 0.8,
                "best_for": "cutting-edge research",
                "redundancy_with": {"semanticscholar": 0.3},
                "last_evaluated": self.base_time.isoformat(),
            },
            "hackernews": {
                "quality_avg": 7.2,
                "quality_scores": [7.0, 7.5, 7.0, 7.5, 7.0],
                "reliability": 0.90,
                "consecutive_failures": 0,
                "depth": "medium",
                "bias": "practical",
                "freshness": "hourly",
                "exclusivity": 0.6,
                "best_for": "industry trends",
                "redundancy_with": {"reddit": 0.4},
                "last_evaluated": self.base_time.isoformat(),
            },
            "semanticscholar": {
                "quality_avg": 8.0,
                "quality_scores": [7.5, 8.0, 8.5, 8.0, 7.5],
                "reliability": 0.85,
                "consecutive_failures": 1,
                "depth": "high",
                "bias": "academic",
                "freshness": "weekly",
                "exclusivity": 0.7,
                "best_for": "paper discovery",
                "redundancy_with": {"arxiv": 0.3},
                "last_evaluated": self.base_time.isoformat(),
            },
            "blog": {
                "quality_avg": 6.5,
                "quality_scores": [6.0, 6.5, 7.0, 6.5, 6.0],
                "reliability": 0.80,
                "consecutive_failures": 2,
                "depth": "medium",
                "bias": "practical",
                "freshness": "weekly",
                "exclusivity": 0.5,
                "best_for": "practical insights",
                "redundancy_with": {"hackernews": 0.2},
                "last_evaluated": self.base_time.isoformat(),
            },
        }

    def generate_personas(self) -> dict:
        """Generate test persona configurations."""
        return {
            "default": {
                "name": "default",
                "description": "Default balanced persona",
                "fetch_strategy": {
                    "primary_sources": ["arxiv", "hackernews"],
                    "ratio": {
                        "tech": 50,
                        "serendipity": 20,
                        "research": 20,
                        "philosophy": 10,
                    },
                    "synthesis_rules": ["Balance depth and breadth"],
                },
                "reading_preferences": {
                    "preferred_length": "long-form",
                    "preferred_style": "deep analysis",
                },
                "delivery_channels": ["discord"],
            },
            "research": {
                "name": "research",
                "description": "Deep research mode for academic content",
                "fetch_strategy": {
                    "primary_sources": ["arxiv", "semanticscholar"],
                    "ratio": {"research": 80, "tech": 20},
                    "synthesis_rules": [
                        "Deep analysis with citations",
                        "Track paper references",
                        "Include methodology details",
                    ],
                },
                "reading_preferences": {
                    "preferred_length": "long-form",
                    "preferred_style": "academic",
                },
                "delivery_channels": ["discord"],
            },
            "casual": {
                "name": "casual",
                "description": "Casual browsing mode for serendipity",
                "fetch_strategy": {
                    "primary_sources": ["hackernews", "blog"],
                    "ratio": {"serendipity": 60, "tech": 30, "philosophy": 10},
                    "synthesis_rules": [
                        "Focus on surprise and novelty",
                        "Lighter analysis",
                        "Include personal connections",
                    ],
                },
                "reading_preferences": {
                    "preferred_length": "medium",
                    "preferred_style": "conversational",
                },
                "delivery_channels": ["telegram"],
            },
        }

    def generate_archive_entries(self, count: int = 20) -> list[dict]:
        """Generate test archive entries."""
        entries = []
        topics_pool = [
            "ai",
            "rust",
            "distributed_systems",
            "quantum_computing",
            "bioinformatics",
        ]

        for i in range(count):
            topic_idx = (i * 2 + self.seed) % len(topics_pool)
            topic = topics_pool[topic_idx]

            entry = {
                "article_id": f"{self.base_time.strftime('%Y%m%d')}_{1000 + i:04d}",
                "title": f"Archived: {topic.replace('_', ' ').title()} Analysis #{i + 1}",
                "topics": [topic, topics_pool[(topic_idx + 1) % len(topics_pool)]],
                "quality_score": 6.0 + (i % 4),
                "source": ["arxiv", "hackernews", "blog"][i % 3],
                "synthesis_style": ["deep_analysis", "comparison", "surprise"][i % 3],
                "delivered_at": (self.base_time + timedelta(days=i)).isoformat(),
                "ritual_id": i + 1,
                "summary": f"Comprehensive analysis of {topic.replace('_', ' ')} developments.",
                "source_urls": [f"https://example.com/source/{i + 1}"],
                "related_articles": [],
            }
            entries.append(entry)

        # Add some cross-links
        for i in range(0, count - 1, 3):
            if i + 1 < count:
                entries[i]["related_articles"].append(entries[i + 1]["article_id"])
                entries[i + 1]["related_articles"].append(entries[i]["article_id"])

        return entries

    def write_fixtures(self, output_dir: str = "tests/fixtures"):
        """Write all test fixtures to disk."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Write memory fixtures
        memory_dir = output_path / "memory"
        memory_dir.mkdir(exist_ok=True)

        memory = self.generate_memory_snapshot()
        with open(memory_dir / "the_only_core.json", "w") as f:
            json.dump(memory["core"], f, indent=2, ensure_ascii=False)
        with open(memory_dir / "the_only_semantic.json", "w") as f:
            json.dump(memory["semantic"], f, indent=2, ensure_ascii=False)
        with open(memory_dir / "the_only_episodic.json", "w") as f:
            json.dump(memory["episodic"], f, indent=2, ensure_ascii=False)

        # Write ritual log
        ritual_log = self.generate_ritual_log()
        with open(memory_dir / "the_only_ritual_log.jsonl", "w") as f:
            for entry in ritual_log:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Write config
        config = {
            "name": "TestBot",
            "frequency": "hourly",
            "items_per_ritual": 5,
            "version": "2.0",
            "webhooks": {
                "discord": "https://discord.com/api/webhooks/test",
                "telegram": {"bot_token": "test_token", "chat_id": "test_chat"},
            },
            "mesh": {
                "enabled": True,
                "auto_publish_threshold": 7.5,
                "network_ratio": 0.2,
            },
        }
        with open(memory_dir / "the_only_config.json", "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # Write source profiles
        sources = self.generate_source_profiles()
        with open(memory_dir / "the_only_source_profiles.json", "w") as f:
            json.dump(sources, f, indent=2, ensure_ascii=False)

        # Write archive
        archive_dir = memory_dir / "the_only_archive"
        archive_dir.mkdir(exist_ok=True)
        archive_entries = self.generate_archive_entries()
        archive_index = {
            "version": "2.0",
            "total_articles": len(archive_entries),
            "entries": archive_entries,
        }
        with open(archive_dir / "index.json", "w") as f:
            json.dump(archive_index, f, indent=2, ensure_ascii=False)

        # Write personas
        personas_dir = output_path / "personas"
        personas_dir.mkdir(exist_ok=True)
        personas = self.generate_personas()
        for name, persona in personas.items():
            with open(personas_dir / f"{name}.json", "w") as f:
                json.dump(persona, f, indent=2, ensure_ascii=False)

        # Write articles
        sources_dir = output_path / "sources"
        sources_dir.mkdir(exist_ok=True)
        articles = self.generate_articles(20)
        with open(sources_dir / "test_articles.json", "w") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)

        print(f"✅ Test fixtures written to {output_path}")
        print(f"   - Memory: {memory_dir}")
        print(f"   - Personas: {personas_dir}")
        print(f"   - Sources: {sources_dir}")


if __name__ == "__main__":
    generator = TestDataGenerator(seed=42)
    generator.write_fixtures()
