#!/usr/bin/env python3
"""
Persona Manager for the_only V2
────────────────────────────────
Manages multiple personas with independent fetch strategies,
reading preferences, and delivery channels.

Usage:
    python3 scripts/persona_manager.py --action list
    python3 scripts/persona_manager.py --action switch --persona research
    python3 scripts/persona_manager.py --action create --persona work --config work.json
    python3 scripts/persona_manager.py --action status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from optimized_io import load_json, save_json, timestamp


PERSONAS_DIR = os.path.expanduser("~/memory/personas")
CURRENT_PERSONA_FILE = os.path.expanduser("~/memory/current_persona.json")

DEFAULT_PERSONA = {
    "name": "default",
    "description": "Default balanced persona",
    "fetch_strategy": {
        "primary_sources": ["arxiv", "hackernews"],
        "exclusions": [],
        "ratio": {"tech": 50, "serendipity": 20, "research": 20, "philosophy": 10},
        "synthesis_rules": ["Balance depth and breadth"],
        "tool_preferences": "web_search for breadth, read_url for depth",
    },
    "reading_preferences": {
        "preferred_length": "long-form",
        "preferred_style": "deep analysis",
        "emotional_vibe": "intellectually curious",
    },
    "delivery_channels": ["discord"],
    "created_at": "",
    "last_used": "",
}


class PersonaManager:
    """Manages multiple personas for the_only."""

    def __init__(self, memory_dir: str = "~/memory"):
        self.memory_dir = os.path.expanduser(memory_dir)
        self.personas_dir = os.path.join(self.memory_dir, "personas")
        self.current_persona_file = os.path.join(
            self.memory_dir, "current_persona.json"
        )

        os.makedirs(self.personas_dir, exist_ok=True)

    def list_personas(self) -> list[str]:
        """List all available personas."""
        personas = []
        if os.path.exists(self.personas_dir):
            for f in os.listdir(self.personas_dir):
                if f.endswith(".json"):
                    personas.append(f[:-5])
        return sorted(personas)

    def get_current_persona(self) -> dict:
        """Get current persona configuration."""
        if os.path.exists(self.current_persona_file):
            data = load_json(self.current_persona_file)
            if data.get("name"):
                persona_file = os.path.join(self.personas_dir, f"{data['name']}.json")
                if os.path.exists(persona_file):
                    return load_json(persona_file, DEFAULT_PERSONA)

        return DEFAULT_PERSONA

    def switch_persona(self, name: str) -> bool:
        """Switch to a persona."""
        persona_file = os.path.join(self.personas_dir, f"{name}.json")
        if not os.path.exists(persona_file):
            print(f"❌ Persona '{name}' not found", file=sys.stderr)
            return False

        persona = load_json(persona_file, DEFAULT_PERSONA)
        persona["last_used"] = timestamp()
        save_json(persona_file, persona)

        save_json(self.current_persona_file, {"name": name, "switched_at": timestamp()})

        print(f"✅ Switched to persona: {name}")
        print(f"   Description: {persona.get('description', 'N/A')}")
        print(f"   Sources: {', '.join(persona['fetch_strategy']['primary_sources'])}")
        return True

    def create_persona(self, name: str, config: dict | None = None) -> bool:
        """Create a new persona."""
        persona_file = os.path.join(self.personas_dir, f"{name}.json")
        if os.path.exists(persona_file):
            print(f"❌ Persona '{name}' already exists", file=sys.stderr)
            return False

        if config:
            persona = config
        else:
            persona = DEFAULT_PERSONA.copy()

        persona["name"] = name
        persona["created_at"] = timestamp()
        persona["last_used"] = timestamp()

        save_json(persona_file, persona)
        print(f"✅ Created persona: {name}")
        return True

    def delete_persona(self, name: str) -> bool:
        """Delete a persona."""
        if name == "default":
            print("❌ Cannot delete default persona", file=sys.stderr)
            return False

        persona_file = os.path.join(self.personas_dir, f"{name}.json")
        if not os.path.exists(persona_file):
            print(f"❌ Persona '{name}' not found", file=sys.stderr)
            return False

        os.remove(persona_file)

        current = self.get_current_persona()
        if current.get("name") == name:
            self.switch_persona("default")

        print(f"✅ Deleted persona: {name}")
        return True

    def get_persona_config(self, name: str) -> dict | None:
        """Get persona configuration by name."""
        persona_file = os.path.join(self.personas_dir, f"{name}.json")
        if os.path.exists(persona_file):
            return load_json(persona_file, DEFAULT_PERSONA)
        return None

    def update_persona(self, name: str, changes: dict) -> bool:
        """Update persona configuration."""
        persona_file = os.path.join(self.personas_dir, f"{name}.json")
        if not os.path.exists(persona_file):
            print(f"❌ Persona '{name}' not found", file=sys.stderr)
            return False

        persona = load_json(persona_file, DEFAULT_PERSONA)

        for key, value in changes.items():
            if key in ["fetch_strategy", "reading_preferences"] and isinstance(
                value, dict
            ):
                if key not in persona:
                    persona[key] = {}
                persona[key].update(value)
            else:
                persona[key] = value

        persona["last_used"] = timestamp()
        save_json(persona_file, persona)
        print(f"✅ Updated persona: {name}")
        return True


def action_list(manager: PersonaManager):
    """List all personas."""
    personas = manager.list_personas()
    current = manager.get_current_persona()

    print("═══ Personas ═══")
    for name in personas:
        marker = "→ " if name == current.get("name") else "  "
        config = manager.get_persona_config(name)
        desc = config.get("description", "N/A") if config else "N/A"
        print(f"{marker}{name}: {desc}")

    print(f"\nCurrent: {current.get('name', 'default')}")


def action_switch(manager: PersonaManager, persona: str):
    """Switch to a persona."""
    manager.switch_persona(persona)


def action_create(manager: PersonaManager, persona: str, config_file: str | None):
    """Create a new persona."""
    if config_file:
        config = load_json(config_file, {})
        if not config:
            print(f"❌ Cannot load config from {config_file}", file=sys.stderr)
            sys.exit(1)
    else:
        config = None

    manager.create_persona(persona, config)


def action_status(manager: PersonaManager):
    """Show persona status."""
    current = manager.get_current_persona()

    print("═══ Current Persona ═══")
    print(f"Name: {current.get('name', 'default')}")
    print(f"Description: {current.get('description', 'N/A')}")

    fetch = current.get("fetch_strategy", {})
    print(f"\n── Fetch Strategy ──")
    print(f"Primary Sources: {', '.join(fetch.get('primary_sources', []))}")
    print(f"Ratio: {fetch.get('ratio', {})}")

    prefs = current.get("reading_preferences", {})
    print(f"\n── Reading Preferences ──")
    print(f"Length: {prefs.get('preferred_length', 'N/A')}")
    print(f"Style: {prefs.get('preferred_style', 'N/A')}")

    print(f"\n── Delivery ──")
    print(f"Channels: {', '.join(current.get('delivery_channels', []))}")


def action_test():
    """Run self-tests."""
    import tempfile

    passed = 0
    failed = 0

    def _assert(condition: bool, name: str):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    with tempfile.TemporaryDirectory(prefix="persona_test_") as tmpdir:
        print("🧪 Running persona manager tests...")

        manager = PersonaManager(tmpdir)

        personas = manager.list_personas()
        _assert(len(personas) == 0, "empty personas dir returns empty list")

        current = manager.get_current_persona()
        _assert(current["name"] == "default", "default persona returned")

        _assert(manager.create_persona("research"), "create research persona")
        _assert(manager.create_persona("casual"), "create casual persona")

        personas = manager.list_personas()
        _assert("research" in personas, "research in list")
        _assert("casual" in personas, "casual in list")

        _assert(manager.switch_persona("research"), "switch to research")
        current = manager.get_current_persona()
        _assert(current["name"] == "research", "current is research")

        _assert(
            manager.update_persona("research", {"description": "Updated"}),
            "update persona",
        )
        config = manager.get_persona_config("research")
        _assert(config["description"] == "Updated", "description updated")

        _assert(manager.delete_persona("casual"), "delete casual")
        personas = manager.list_personas()
        _assert("casual" not in personas, "casual removed")

        _assert(not manager.delete_persona("default"), "cannot delete default")

    print(f"\n{'=' * 40}")
    print(f"Results: {passed}/{passed + failed} passed, {failed} failed")
    if failed > 0:
        print("❌ SOME TESTS FAILED", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ All tests passed")


def main():
    parser = argparse.ArgumentParser(description="Persona Manager for the_only V2")
    parser.add_argument(
        "--action",
        choices=["list", "switch", "create", "delete", "status", "test"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--persona", help="Persona name")
    parser.add_argument("--config", help="Config file for create")
    parser.add_argument("--memory-dir", default="~/memory", help="Memory directory")

    args = parser.parse_args()
    manager = PersonaManager(args.memory_dir)

    if args.action == "list":
        action_list(manager)
    elif args.action == "switch":
        if not args.persona:
            print("❌ --persona required for switch", file=sys.stderr)
            sys.exit(1)
        action_switch(manager, args.persona)
    elif args.action == "create":
        if not args.persona:
            print("❌ --persona required for create", file=sys.stderr)
            sys.exit(1)
        action_create(manager, args.persona, args.config)
    elif args.action == "delete":
        if not args.persona:
            print("❌ --persona required for delete", file=sys.stderr)
            sys.exit(1)
        manager.delete_persona(args.persona)
    elif args.action == "status":
        action_status(manager)
    elif args.action == "test":
        action_test()


if __name__ == "__main__":
    main()
