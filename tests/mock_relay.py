#!/usr/bin/env python3
"""
Mock Nostr Relay for Testing
─────────────────────────────
Simulates a Nostr relay for deterministic testing of Mesh operations.
Stores events in memory and provides query interfaces.

Usage:
    from tests.mock_relay import MockRelay
    relay = MockRelay()
    relay.publish(event)
    events = relay.query(filter)
"""

from __future__ import annotations

import json
import time
from typing import Any


class MockRelay:
    """Simulates a Nostr relay for testing."""

    def __init__(self):
        self.events: list[dict] = []
        self.subscriptions: dict[str, dict] = {}

    def publish(self, event: dict) -> bool:
        """Publish an event to the relay."""
        if self._validate_event(event):
            self.events.append(event)
            return True
        return False

    def query(self, filter: dict) -> list[dict]:
        """Query events matching the filter."""
        results = []
        for event in self.events:
            if self._matches_filter(event, filter):
                results.append(event)
        return results

    def subscribe(self, subscription_id: str, filter: dict) -> list[dict]:
        """Subscribe to events matching the filter."""
        self.subscriptions[subscription_id] = filter
        return self.query(filter)

    def unsubscribe(self, subscription_id: str):
        """Unsubscribe from events."""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]

    def _validate_event(self, event: dict) -> bool:
        """Validate event structure."""
        required_fields = [
            "id",
            "pubkey",
            "created_at",
            "kind",
            "tags",
            "content",
            "sig",
        ]
        return all(field in event for field in required_fields)

    def _matches_filter(self, event: dict, filter: dict) -> bool:
        """Check if event matches filter."""
        if "ids" in filter and event["id"] not in filter["ids"]:
            return False
        if "authors" in filter and event["pubkey"] not in filter["authors"]:
            return False
        if "kinds" in filter and event["kind"] not in filter["kinds"]:
            return False
        if "since" in filter and event["created_at"] < filter["since"]:
            return False
        if "until" in filter and event["created_at"] > filter["until"]:
            return False
        if "#t" in filter:
            event_tags = [tag[1] for tag in event.get("tags", []) if tag[0] == "t"]
            if not any(tag in event_tags for tag in filter["#t"]):
                return False
        return True

    def clear(self):
        """Clear all events."""
        self.events.clear()
        self.subscriptions.clear()

    def get_event_count(self) -> int:
        """Get total event count."""
        return len(self.events)

    def get_events_by_kind(self, kind: int) -> list[dict]:
        """Get all events of a specific kind."""
        return [e for e in self.events if e["kind"] == kind]
