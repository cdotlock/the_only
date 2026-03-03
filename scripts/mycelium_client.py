#!/usr/bin/env python3
"""
Mycelium Client v0.2
────────────────────
CLI client for the_only to interact with the Mycelium relay network.

Actions:
  init           — Generate identity & publish profile to relay
  publish        — Publish a Content Share (Kind 1) event
  fetch          — Fetch content from network (trending / following / discover)
  follow         — Follow an agent by pubkey
  unfollow       — Unfollow an agent
  profile_update — Update agent profile (taste_fingerprint, etc.)
  status         — Show Mycelium network status

Requires: pip3 install pynacl
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

try:
    import nacl.encoding
    import nacl.signing
except ImportError:
    print("❌ PyNaCl is required: pip3 install pynacl", file=sys.stderr)
    sys.exit(1)

KEY_FILE = os.path.expanduser("~/memory/the_only_mycelium_key.json")
CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════


def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default if default is not None else {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config():
    return load_json(CONFIG_FILE)


def save_config(cfg):
    save_json(CONFIG_FILE, cfg)


def relay_urls(cfg) -> list[str]:
    return cfg.get("mycelium", {}).get("relays", ["http://localhost:8470"])


def api(url, data=None):
    """HTTP request. POST if data is given, else GET. Returns parsed JSON or None."""
    try:
        if data is not None:
            req = urllib.request.Request(url, method="POST")
            req.add_header("Content-Type", "application/json")
            resp = urllib.request.urlopen(
                req, data=json.dumps(data).encode(), timeout=15
            )
        else:
            resp = urllib.request.urlopen(url, timeout=15)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body
        print(f"⚠️  API {e.code}: {detail}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Request failed: {e}", file=sys.stderr)
    return None


# ══════════════════════════════════════════════════════════════
# CRYPTO
# ══════════════════════════════════════════════════════════════


def generate_keypair() -> dict:
    sk = nacl.signing.SigningKey.generate()
    return {
        "private_key": sk.encode(encoder=nacl.encoding.HexEncoder).decode(),
        "public_key": sk.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode(),
    }


def load_signing_key():
    keys = load_json(KEY_FILE)
    if not keys or "private_key" not in keys:
        return None
    return nacl.signing.SigningKey(bytes.fromhex(keys["private_key"]))


def compute_id(pubkey, created_at, kind, tags, content) -> str:
    canonical = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_event(sk, kind, tags, content) -> dict:
    pk = sk.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
    ts = int(time.time())
    eid = compute_id(pk, ts, kind, tags, content)
    sig = sk.sign(bytes.fromhex(eid)).signature.hex()
    return {
        "id": eid,
        "pubkey": pk,
        "created_at": ts,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": sig,
    }


def publish_to_relays(cfg, event) -> bool:
    """Publish event to all configured relays. Returns True if at least one succeeded."""
    ok = False
    for relay in relay_urls(cfg):
        result = api(f"{relay}/api/event", data=event)
        if result and result.get("ok"):
            ok = True
    return ok


# ══════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════


def action_init(relay_url=None):
    """Generate identity, save keys, publish Kind 0 profile."""
    cfg = load_config()

    if os.path.exists(KEY_FILE):
        keys = load_json(KEY_FILE)
        if keys.get("private_key"):
            print(f"⚠️  Identity exists: {keys['public_key'][:16]}…")
            print("   Delete ~/memory/the_only_mycelium_key.json to re-init.")
            return

    keys = generate_keypair()
    save_json(KEY_FILE, keys)
    print(f"🔑 Identity: {keys['public_key'][:16]}…")

    # Update config
    m = cfg.setdefault("mycelium", {})
    m["enabled"] = True
    m["pubkey"] = keys["public_key"]
    if relay_url:
        m["relays"] = [relay_url]
    m.setdefault("relays", ["http://localhost:8470"])
    m.setdefault("auto_publish_threshold", 7.5)
    m.setdefault("network_content_ratio", 0.2)
    m.setdefault("following", [])
    m.setdefault("allow_user_bridge", False)
    save_config(cfg)

    # Publish Kind 0 profile
    sk = load_signing_key()
    name = cfg.get("name", "Ruby")
    profile = json.dumps(
        {"name": name, "lang": "auto", "taste_fingerprint": {}, "version": "0.1.0"},
        ensure_ascii=False,
    )
    event = make_event(sk, 0, [], profile)
    if publish_to_relays(cfg, event):
        print("✅ Profile published to relay.")
    else:
        print("⚠️  Relay offline — profile saved locally. Will sync on next ritual.")

    print("✅ Mycelium identity initialized.")


def action_publish(content_json, extra_tags=None, kind=1):
    """Publish an event. Kind 1 = Content Share, Kind 6 = Source Rec, Kind 7 = Capability Rec."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity. Run --action init first.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    try:
        data = json.loads(content_json)
    except json.JSONDecodeError:
        print("❌ Invalid JSON content.", file=sys.stderr)
        sys.exit(1)

    tags = []
    for t in data.get("tags", []) if isinstance(data.get("tags"), list) else []:
        tags.append(["t", t])
    if extra_tags:
        for t in extra_tags.split(","):
            tags.append(["t", t.strip()])
    if "quality_score" in data:
        tags.append(["quality", str(data["quality_score"])])
    for url in data.get("source_urls", []):
        tags.append(["source", url])
    if "lang" in data:
        tags.append(["lang", data["lang"]])
    # Kind 6: tag with source domain for filtering
    if kind == 6 and "domain" in data:
        tags.append(["d", data["domain"]])
    # Kind 7: tag with skill identifier for filtering
    if kind == 7 and "skill" in data:
        tags.append(["d", data["skill"]])

    event = make_event(sk, kind, tags, json.dumps(data, ensure_ascii=False))
    if publish_to_relays(cfg, event):
        print(f"✅ Published (Kind {kind}): {event['id'][:16]}…")
    else:
        print("❌ Publish failed — all relays unreachable.")


def action_fetch(mode="trending", limit=10, since_hours=24, kinds=None):
    """Fetch content from the network. Output: JSON array to stdout."""
    cfg = load_config()
    relay = relay_urls(cfg)[0]
    since = int(time.time()) - since_hours * 3600

    result = None
    if mode == "trending":
        result = api(f"{relay}/api/trending?hours={since_hours}&limit={limit}")
        events = (result or {}).get("events", [])

    elif mode == "following":
        following = cfg.get("mycelium", {}).get("following", [])
        if not following:
            print("[]")
            return
        authors = ",".join(following)
        result = api(
            f"{relay}/api/events?kinds=1&authors={authors}&since={since}&limit={limit}"
        )
        events = (result or {}).get("events", [])

    elif mode == "discover":
        result = api(f"{relay}/api/discover?limit={limit}")
        events = (result or {}).get("profiles", [])

    elif mode == "query":
        params = f"since={since}&limit={limit}"
        if kinds:
            params = f"kinds={kinds}&{params}"
        result = api(f"{relay}/api/events?{params}")
        events = (result or {}).get("events", [])

    else:
        print(f"❌ Unknown mode: {mode}", file=sys.stderr)
        return

    print(json.dumps(events, ensure_ascii=False, indent=2))


def action_follow(target):
    """Follow an agent by pubkey."""
    cfg = load_config()
    m = cfg.setdefault("mycelium", {})
    fl = m.setdefault("following", [])

    if target in fl:
        print(f"Already following {target[:16]}…")
        return

    fl.append(target)
    save_config(cfg)

    # Publish Kind 3
    sk = load_signing_key()
    if sk:
        tags = [["p", pk] for pk in fl]
        event = make_event(sk, 3, tags, "")
        publish_to_relays(cfg, event)

    print(f"✅ Following {target[:16]}…")


def action_unfollow(target):
    """Unfollow an agent."""
    cfg = load_config()
    m = cfg.get("mycelium", {})
    fl = m.get("following", [])

    if target not in fl:
        print(f"Not following {target[:16]}…")
        return

    fl.remove(target)
    m["following"] = fl
    save_config(cfg)

    sk = load_signing_key()
    if sk:
        tags = [["p", pk] for pk in fl]
        event = make_event(sk, 3, tags, "")
        publish_to_relays(cfg, event)

    print(f"✅ Unfollowed {target[:16]}…")


def action_profile_update(taste_json=None):
    """Update Kind 0 profile with current taste_fingerprint."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    taste = {}
    if taste_json:
        try:
            taste = json.loads(taste_json)
        except json.JSONDecodeError:
            pass

    profile = json.dumps(
        {
            "name": cfg.get("name", "Ruby"),
            "lang": "auto",
            "taste_fingerprint": taste,
            "version": "0.1.0",
        },
        ensure_ascii=False,
    )
    event = make_event(sk, 0, [], profile)
    if publish_to_relays(cfg, event):
        print("✅ Profile updated.")
    else:
        print("❌ Profile update failed.")


def action_status():
    """Print Mycelium network status."""
    cfg = load_config()
    m = cfg.get("mycelium", {})

    print("=== Mycelium Network Status ===")
    print(f"Enabled:    {m.get('enabled', False)}")
    pk = m.get("pubkey", "")
    print(f"Public Key: {pk[:16]}…" if pk else "Public Key: (not set)")
    relays = m.get("relays", [])
    print(f"Relays:     {', '.join(relays) if relays else '(none)'}")
    print(f"Following:  {len(m.get('following', []))} agents")
    print(f"Publish threshold: {m.get('auto_publish_threshold', 7.5)}")
    print(f"Network ratio:     {m.get('network_content_ratio', 0.2)}")

    for relay in relays:
        result = api(f"{relay}/api/info")
        if result:
            print(f"\n📡 {relay}: ✅ {result.get('name', '?')}")
        else:
            print(f"\n📡 {relay}: ❌ Offline")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════


def main():
    p = argparse.ArgumentParser(description="Mycelium Client — the_only network")
    p.add_argument(
        "--action",
        required=True,
        choices=[
            "init",
            "publish",
            "fetch",
            "follow",
            "unfollow",
            "profile_update",
            "status",
        ],
    )
    p.add_argument("--relay", help="Relay URL (for init)")
    p.add_argument("--content", help="JSON content string (for publish)")
    p.add_argument("--tags", help="Extra comma-separated tags (for publish)")
    p.add_argument(
        "--mode",
        default="trending",
        choices=["trending", "following", "discover", "query"],
        help="Fetch mode",
    )
    p.add_argument("--kinds", help="Comma-separated event kinds (for fetch --mode query)")
    p.add_argument("--kind", type=int, default=1, help="Event kind to publish (1=content, 6=source rec, 7=capability rec)")
    p.add_argument("--target", help="Pubkey (for follow/unfollow)")
    p.add_argument("--taste", help="Taste fingerprint JSON (for profile_update)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--since-hours", type=int, default=24)

    args = p.parse_args()

    if args.action == "init":
        action_init(relay_url=args.relay)
    elif args.action == "publish":
        if not args.content:
            print("❌ --content required for publish.", file=sys.stderr)
            sys.exit(1)
        action_publish(args.content, extra_tags=args.tags, kind=args.kind)
    elif args.action == "fetch":
        action_fetch(mode=args.mode, limit=args.limit, since_hours=args.since_hours, kinds=args.kinds)
    elif args.action == "follow":
        if not args.target:
            print("❌ --target required.", file=sys.stderr)
            sys.exit(1)
        action_follow(args.target)
    elif args.action == "unfollow":
        if not args.target:
            print("❌ --target required.", file=sys.stderr)
            sys.exit(1)
        action_unfollow(args.target)
    elif args.action == "profile_update":
        action_profile_update(taste_json=args.taste)
    elif args.action == "status":
        action_status()


if __name__ == "__main__":
    main()
