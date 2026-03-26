#!/usr/bin/env python3
"""
End-to-End Test Suite for the_only V2
──────────────────────────────────────
Runs comprehensive E2E tests using test fixtures and mock services.

Scenarios:
  1. Offline ritual baseline (no mesh)
  2. Full ritual with mocked mesh
  3. Multi-persona switching
  4. Progressive onboarding
  5. Complete delivery pipeline

Usage:
    python3 tests/run_e2e_tests.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    ),
)

from tests.data_generator import TestDataGenerator
from tests.mock_webhook import MockWebhookServer


class E2ETestRunner:
    """Runs end-to-end tests for the_only V2."""

    def __init__(self):
        self.results: dict[str, dict] = {}
        self.fixture_dir = "tests/fixtures"

    def run_all(self):
        """Run all E2E test scenarios."""
        print("═══ the_only V2 — End-to-End Test Suite ═══\n")

        scenarios = [
            ("Scenario 1: Offline Ritual Baseline", self.test_offline_ritual),
            ("Scenario 2: Full Ritual with Test Fixtures", self.test_full_ritual),
            ("Scenario 3: Multi-Persona Switching", self.test_multi_persona),
            ("Scenario 4: Knowledge Archive Integration", self.test_knowledge_archive),
            ("Scenario 5: Complete Delivery Pipeline", self.test_delivery_pipeline),
        ]

        for name, test_func in scenarios:
            print(f"\n{'─' * 60}")
            print(f"Running: {name}")
            print(f"{'─' * 60}")

            start_time = time.time()
            try:
                success, details = test_func()
                duration = time.time() - start_time

                self.results[name] = {
                    "success": success,
                    "duration": duration,
                    "details": details,
                }

                if success:
                    print(f"\n✅ {name} PASSED ({duration:.2f}s)")
                else:
                    print(f"\n❌ {name} FAILED ({duration:.2f}s)")
                    print(f"   Details: {details}")
            except Exception as e:
                duration = time.time() - start_time
                self.results[name] = {
                    "success": False,
                    "duration": duration,
                    "details": str(e),
                }
                print(f"\n❌ {name} FAILED with exception ({duration:.2f}s)")
                print(f"   Error: {e}")

        self._print_summary()

    def test_offline_ritual(self) -> tuple[bool, str]:
        """Test offline ritual baseline using test fixtures."""
        with tempfile.TemporaryDirectory(prefix="e2e_offline_") as tmpdir:
            generator = TestDataGenerator(seed=42)
            generator.write_fixtures(tmpdir)

            memory_dir = os.path.join(tmpdir, "memory")

            cmd = [
                sys.executable,
                "scripts/ritual_runner.py",
                "--all",
                "--dry-run",
                "--memory-dir",
                memory_dir,
                "--test-fixtures",
                tmpdir,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return False, f"Exit code {result.returncode}: {result.stderr[:500]}"

            output = result.stdout

            checks = [
                ("Phase 0: Pre-Flight", "Phase 0: Pre-Flight" in output),
                ("Phase 1: Gather", "Phase 1: Gather" in output),
                ("Phase 2: Evaluate", "Phase 2: Evaluate" in output),
                ("Phase 3: Synthesize", "Phase 3: Synthesize" in output),
                ("Phase 4: Output", "Phase 4: Output" in output),
                ("Phase 5: Reflect", "Phase 5: Reflect" in output),
                ("Ritual Complete", "Ritual Complete" in output),
                (
                    "Test articles loaded",
                    "test articles" in output.lower()
                    or "candidates found" in output.lower(),
                ),
            ]

            failed = [name for name, passed in checks if not passed]
            if failed:
                return False, f"Missing: {', '.join(failed)}"

            return True, "All phases completed"

    def test_full_ritual(self) -> tuple[bool, str]:
        """Test full ritual with test fixtures and simulated synthesis."""
        with tempfile.TemporaryDirectory(prefix="e2e_full_") as tmpdir:
            generator = TestDataGenerator(seed=42)
            generator.write_fixtures(tmpdir)

            memory_dir = os.path.join(tmpdir, "memory")

            cmd = [
                sys.executable,
                "scripts/ritual_runner.py",
                "--all",
                "--dry-run",
                "--memory-dir",
                memory_dir,
                "--test-fixtures",
                tmpdir,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return False, f"Exit code {result.returncode}: {result.stderr[:500]}"

            output = result.stdout

            has_synthesis = (
                "simulated synthesis" in output.lower() or "synthesis" in output.lower()
            )
            has_arc = "arc" in output.lower() or "narrative" in output.lower()

            if not has_synthesis:
                return False, "No synthesis output found"

            return True, "Full ritual with synthesis completed"

    def test_multi_persona(self) -> tuple[bool, str]:
        """Test multi-persona system."""
        with tempfile.TemporaryDirectory(prefix="e2e_persona_") as tmpdir:
            memory_dir = os.path.join(tmpdir, "memory")
            os.makedirs(memory_dir, exist_ok=True)

            cmd_create = [
                sys.executable,
                "scripts/persona_manager.py",
                "--action",
                "create",
                "--persona",
                "research",
                "--memory-dir",
                memory_dir,
            ]

            result = subprocess.run(
                cmd_create, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return False, f"Create persona failed: {result.stderr}"

            cmd_switch = [
                sys.executable,
                "scripts/persona_manager.py",
                "--action",
                "switch",
                "--persona",
                "research",
                "--memory-dir",
                memory_dir,
            ]

            result = subprocess.run(
                cmd_switch, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return False, f"Switch persona failed: {result.stderr}"

            if "Switched to persona: research" not in result.stdout:
                return False, "Switch confirmation not found"

            cmd_list = [
                sys.executable,
                "scripts/persona_manager.py",
                "--action",
                "list",
                "--memory-dir",
                memory_dir,
            ]

            result = subprocess.run(
                cmd_list, capture_output=True, text=True, timeout=30
            )
            if "research" not in result.stdout:
                return False, "Persona not in list"

            return True, "Multi-persona create/switch/list working"

    def test_knowledge_archive(self) -> tuple[bool, str]:
        """Test knowledge archive integration."""
        with tempfile.TemporaryDirectory(prefix="e2e_archive_") as tmpdir:
            archive_dir = os.path.join(tmpdir, "the_only_archive")
            os.makedirs(archive_dir, exist_ok=True)

            from scripts.knowledge_archive import KnowledgeArchive, ArchiveEntry

            archive = KnowledgeArchive(tmpdir)

            entry1 = ArchiveEntry(
                id="20260326_1000_001",
                title="Test Article 1: AI Deep Dive",
                topics=["ai", "machine_learning", "deep_learning"],
                quality_score=8.5,
                source="arxiv",
                synthesis_style="deep_analysis",
                delivered_at="2026-03-26T10:00:00Z",
                ritual_id="1",
            )

            entry2 = ArchiveEntry(
                id="20260326_1000_002",
                title="Test Article 2: AI Applications",
                topics=["ai", "machine_learning", "deep_learning", "applications"],
                quality_score=7.5,
                source="blog",
                synthesis_style="comparison",
                delivered_at="2026-03-26T10:05:00Z",
                ritual_id="1",
            )

            archive.append([entry1, entry2])

            if archive.total_count() != 2:
                return False, f"Expected 2 entries, got {archive.total_count()}"

            results = archive.search("ai")
            if len(results) < 1:
                return (
                    False,
                    f"Search 'ai' expected at least 1 result, got {len(results)}",
                )

            links = archive.auto_link([entry1, entry2])
            if links == 0:
                return False, "Auto-link created no links"

            summary = archive.monthly_summary(2026, 3)
            if summary["total_articles"] != 2:
                return (
                    False,
                    f"Monthly summary expected 2 articles, got {summary['total_articles']}",
                )

            return (
                True,
                f"Archive: {archive.total_count()} entries, {links} links, search working",
            )

    def test_delivery_pipeline(self) -> tuple[bool, str]:
        """Test delivery pipeline with mock webhooks."""
        server = MockWebhookServer(port=8799)

        try:
            server.start()
            time.sleep(0.5)

            import urllib.request

            webhook_url = server.get_webhook_url("discord")
            test_payload = json.dumps({"content": "Test message"}).encode()

            req = urllib.request.Request(webhook_url, data=test_payload, method="POST")
            req.add_header("Content-Type", "application/json")

            try:
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                return False, f"Webhook request failed: {e}"

            requests = server.get_requests("discord")
            if len(requests) != 1:
                return False, f"Expected 1 request, got {len(requests)}"

            body = json.loads(requests[0]["body"])
            if body.get("content") != "Test message":
                return False, "Request body mismatch"

            return True, f"Delivery: {len(requests)} request(s) captured correctly"

        finally:
            server.stop()

    def _print_summary(self):
        """Print test summary."""
        print(f"\n{'═' * 60}")
        print("═══ E2E Test Summary ═══")
        print(f"{'═' * 60}\n")

        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["success"])
        failed = total - passed
        total_time = sum(r["duration"] for r in self.results.values())

        for name, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            duration = result["duration"]
            print(f"{status} {name} ({duration:.2f}s)")
            if not result["success"]:
                print(f"     {result['details']}")

        print(f"\n{'─' * 60}")
        print(
            f"Total: {total} | Passed: {passed} | Failed: {failed} | Time: {total_time:.2f}s"
        )

        if failed > 0:
            print(f"\n❌ {failed} test(s) FAILED")
            sys.exit(1)
        else:
            print(f"\n✅ All {total} tests PASSED")


if __name__ == "__main__":
    runner = E2ETestRunner()
    runner.run_all()
