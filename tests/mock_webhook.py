#!/usr/bin/env python3
"""
Mock Webhook Endpoints for Testing
────────────────────────────────────
Simulates webhook receivers for Discord, Telegram, WhatsApp, and Feishu.
Stores requests for verification.

Usage:
    from tests.mock_webhook import MockWebhookServer
    server = MockWebhookServer()
    server.start()
    # ... run tests ...
    requests = server.get_requests("discord")
    server.stop()
"""

from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mock webhooks."""

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        path = urlparse(self.path).path
        platform = path.strip("/").split("/")[0] if path.strip("/") else "unknown"

        request_data = {
            "platform": platform,
            "path": path,
            "headers": dict(self.headers),
            "body": body.decode("utf-8", errors="replace"),
            "timestamp": self.server.get_timestamp(),
        }

        self.server.record_request(request_data)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class MockWebhookServer:
    """Manages mock webhook endpoints."""

    def __init__(self, port: int = 8787):
        self.port = port
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.requests: dict[str, list[dict]] = {
            "discord": [],
            "telegram": [],
            "whatsapp": [],
            "feishu": [],
            "unknown": [],
        }
        self._timestamp_counter = 0

    def start(self):
        """Start the mock server."""
        self.server = HTTPServer(("localhost", self.port), WebhookHandler)
        self.server.record_request = self._record_request
        self.server.get_timestamp = self._get_timestamp
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def _record_request(self, request_data: dict):
        """Record a request."""
        platform = request_data.get("platform", "unknown")
        if platform not in self.requests:
            platform = "unknown"
        self.requests[platform].append(request_data)

    def _get_timestamp(self) -> int:
        """Get incrementing timestamp."""
        self._timestamp_counter += 1
        return self._timestamp_counter

    def get_requests(self, platform: str) -> list[dict]:
        """Get requests for a platform."""
        return self.requests.get(platform, [])

    def get_all_requests(self) -> dict[str, list[dict]]:
        """Get all requests."""
        return self.requests

    def clear(self):
        """Clear all recorded requests."""
        for platform in self.requests:
            self.requests[platform].clear()

    def get_request_count(self, platform: str | None = None) -> int:
        """Get request count."""
        if platform:
            return len(self.requests.get(platform, []))
        return sum(len(reqs) for reqs in self.requests.values())

    def get_webhook_url(self, platform: str) -> str:
        """Get webhook URL for a platform."""
        return f"http://localhost:{self.port}/{platform}/webhook"
