#!/usr/bin/env python3
"""
Optimized I/O Module for the_only v2
─────────────────────────────────────
Provides high-performance JSON I/O using orjson,
Pydantic models for validation, and caching utilities.

Usage:
    from optimized_io import load_json, save_json, cached, run_parallel
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable, TypeVar, Optional, Dict, List
from datetime import datetime, timezone

import orjson
from pydantic import BaseModel, Field, validator

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

T = TypeVar("T")

# ══════════════════════════════════════════════════════════════
# OPTIMIZED JSON I/O (5x faster than stdlib json)
# ══════════════════════════════════════════════════════════════


def load_json(path: str | Path, default: Any = None) -> Any:
    """Load JSON using orjson (5x faster than stdlib)."""
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    try:
        data = p.read_bytes()
        return orjson.loads(data)
    except (orjson.JSONDecodeError, OSError):
        return default


def save_json(path: str | Path, data: Any, pretty: bool = True) -> None:
    """Save JSON using orjson (5x faster than stdlib)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    flags = orjson.OPT_INDENT_2 if pretty else 0
    p.write_bytes(orjson.dumps(data, option=flags | orjson.OPT_NON_STR_KEYS))


def load_json_cached(
    path: str | Path, cache: Dict[str, Any], default: Any = None
) -> Any:
    """Load JSON with in-memory cache (avoids repeated disk reads)."""
    path_str = str(path)
    stat_key = f"{path_str}:mtime"

    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        return default if default is not None else {}

    cached_mtime = cache.get(stat_key, 0)
    if path_str in cache and cached_mtime == current_mtime:
        return cache[path_str]

    data = load_json(path, default)
    cache[path_str] = data
    cache[stat_key] = current_mtime
    return data


# ══════════════════════════════════════════════════════════════
# PYDANTIC MODELS FOR TYPE SAFETY
# ══════════════════════════════════════════════════════════════


class CoreIdentity(BaseModel):
    """Core identity model."""

    current_focus: List[str] = Field(default_factory=list)
    professional_domain: str = ""
    knowledge_level: Dict[str, str] = Field(default_factory=dict)
    values: List[str] = Field(default_factory=list)
    anti_interests: List[str] = Field(default_factory=list)


class ReadingPreferences(BaseModel):
    """Reading preferences model."""

    preferred_length: str = "long-form"
    preferred_style: str = "deep analysis"
    emotional_vibe: str = "intellectually curious"


class CoreMemory(BaseModel):
    """Core memory tier (Tier 1)."""

    version: str = "2.0"
    identity: CoreIdentity = Field(default_factory=CoreIdentity)
    reading_preferences: ReadingPreferences = Field(default_factory=ReadingPreferences)
    established_at: str = ""
    last_validated: str = ""


class FetchStrategy(BaseModel):
    """Fetch strategy model."""

    primary_sources: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    ratio: Dict[str, int] = Field(
        default_factory=lambda: {
            "tech": 50,
            "serendipity": 20,
            "research": 15,
            "philosophy": 15,
        }
    )
    synthesis_rules: List[str] = Field(default_factory=list)
    tool_preferences: str = ""


class SourceProfile(BaseModel):
    """Source intelligence profile."""

    quality_avg: float = 0.0
    quality_scores: List[float] = Field(default_factory=list)
    reliability: float = 1.0
    consecutive_failures: int = 0
    depth: str = "medium"
    bias: str = ""
    freshness: str = "daily"
    exclusivity: float = 0.0
    best_for: str = ""
    redundancy_with: Dict[str, float] = Field(default_factory=dict)
    last_evaluated: str = ""


class EmergingInterest(BaseModel):
    """Emerging interest model."""

    topic: str
    signal_count: int = 1
    first_seen: str = ""
    status: str = "monitoring"


class SemanticMemory(BaseModel):
    """Semantic memory tier (Tier 2)."""

    version: str = "2.0"
    last_compressed: str = ""
    fetch_strategy: FetchStrategy = Field(default_factory=FetchStrategy)
    source_intelligence: Dict[str, SourceProfile] = Field(default_factory=dict)
    engagement_patterns: Dict[str, Any] = Field(default_factory=dict)
    temporal_patterns: Dict[str, Any] = Field(default_factory=dict)
    synthesis_effectiveness: Dict[str, Any] = Field(default_factory=dict)
    emerging_interests: List[EmergingInterest] = Field(default_factory=list)
    evolution_log: List[Dict[str, Any]] = Field(default_factory=list)


class EngagementData(BaseModel):
    """Per-item engagement data."""

    score: int = 0
    signal: str = ""
    topic: str = ""


class EpisodicEntry(BaseModel):
    """Single episodic entry."""

    ritual_id: int = 0
    timestamp: str = ""
    items_delivered: int = 0
    avg_quality_score: float = 0.0
    categories: Dict[str, int] = Field(default_factory=dict)
    engagement: Dict[str, EngagementData] = Field(default_factory=dict)
    sources_used: List[str] = Field(default_factory=list)
    sources_failed: List[str] = Field(default_factory=list)
    echo_fulfilled: bool = False
    network_items: int = 0
    search_queries: int = 0
    narrative_theme: str = ""
    synthesis_styles: Dict[str, int] = Field(default_factory=dict)
    self_notes: str = ""


class EpisodicMemory(BaseModel):
    """Episodic memory tier (Tier 3)."""

    version: str = "2.0"
    entries: List[EpisodicEntry] = Field(default_factory=list)


class ArchiveEntry(BaseModel):
    """Knowledge archive entry."""

    article_id: str = ""
    title: str = ""
    topics: List[str] = Field(default_factory=list)
    quality_score: float = 0.0
    source: str = ""
    synthesis_style: str = ""
    delivered_at: str = ""
    ritual_id: int = 0
    summary: str = ""
    source_urls: List[str] = Field(default_factory=list)
    related_articles: List[str] = Field(default_factory=list)


class CandidateItem(BaseModel):
    """Candidate item for ritual pipeline."""

    title: str = ""
    content: str = ""
    source: str = ""
    url: str = ""
    topics: List[str] = Field(default_factory=list)
    quality_score: float = 0.0
    relevance_score: float = 0.0
    freshness_score: float = 0.0
    depth_score: float = 0.0
    uniqueness_score: float = 0.0
    actionability_score: float = 0.0
    composite_score: float = 0.0
    curation_reason: str = ""
    is_serendipity: bool = False
    is_echo: bool = False
    from_mesh: bool = False
    narrative_position: str = ""


# ══════════════════════════════════════════════════════════════
# CACHING UTILITIES
# ══════════════════════════════════════════════════════════════


class LRUCache:
    """Simple LRU cache with max size."""

    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self.cache: Dict[str, Any] = {}
        self.order: List[str] = []

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.maxsize:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.order.append(key)

    def clear(self) -> None:
        self.cache.clear()
        self.order.clear()


def cached(maxsize: int = 128):
    """Decorator for caching function results."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = LRUCache(maxsize)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            result = cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(key, result)
            return result

        wrapper.cache = cache
        return wrapper

    return decorator


# ══════════════════════════════════════════════════════════════
# PARALLEL EXECUTION
# ══════════════════════════════════════════════════════════════


def run_parallel(funcs: List[Callable], max_workers: int = 4) -> List[Any]:
    """Run functions in parallel using ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(f) for f in funcs]
        return [f.result() for f in futures]


async def run_parallel_async(funcs: List[Callable], max_workers: int = 4) -> List[Any]:
    """Run functions in parallel using asyncio."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = [loop.run_in_executor(executor, f) for f in funcs]
        return await asyncio.gather(*tasks)


# ══════════════════════════════════════════════════════════════
# TIMESTAMP UTILITIES
# ══════════════════════════════════════════════════════════════


def timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def timestamp_short() -> str:
    """Return current timestamp in compact format."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")


# ══════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ══════════════════════════════════════════════════════════════


def validate_or_default(data: dict, model_class: type[BaseModel]) -> BaseModel:
    """Validate data against Pydantic model, return default on failure."""
    try:
        return model_class(**data)
    except Exception:
        return model_class()


def deep_merge(target: dict, defaults: dict) -> dict:
    """Recursively fill missing keys in target from defaults."""
    for key, default_val in defaults.items():
        if key not in target:
            target[key] = default_val
        elif isinstance(default_val, dict) and isinstance(target[key], dict):
            deep_merge(target[key], default_val)
    return target
