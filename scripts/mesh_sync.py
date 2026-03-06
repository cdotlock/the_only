#!/usr/bin/env python3
"""
Mesh Sync v1.0
──────────────
Serverless P2P agent network for the_only.
Each agent publishes signed events to a GitHub Gist.
Other agents sync by reading each other's Gists.
No relay server needed.

Actions:
  init           — Generate Ed25519 identity + create GitHub Gist
  publish        — Sign event, append to local log, push to Gist
  sync           — Pull updates from followed agents' Gists
  discover       — Find new agents via gossip (friends-of-friends)
  follow         — Follow an agent by pubkey
  unfollow       — Unfollow an agent
  profile_update — Update taste fingerprint
  status         — Show mesh network status

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

# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

KEY_FILE = os.path.expanduser("~/memory/the_only_mycelium_key.json")
CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")
PEERS_FILE = os.path.expanduser("~/memory/the_only_peers.json")
MY_LOG_FILE = os.path.expanduser("~/memory/the_only_mesh_log.jsonl")
PEER_LOGS_DIR = os.path.expanduser("~/memory/the_only_peer_logs")
BOOTSTRAP_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mesh", "bootstrap_peers.json")

GIST_API = "https://api.github.com/gists"
GIST_RAW = "https://gist.githubusercontent.com"

MAX_LOG_ENTRIES = 200  # Per-agent log cap (90 days ≈ 180 entries at 2/day)
TASTE_SIMILARITY_THRESHOLD = 0.3  # Cosine similarity threshold for auto-follow


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


def load_peers():
    return load_json(PEERS_FILE, {"peers": {}})


def save_peers(peers):
    save_json(PEERS_FILE, peers)


def load_my_log() -> list[dict]:
    """Load local signed event log."""
    entries = []
    if os.path.exists(MY_LOG_FILE):
        with open(MY_LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return entries


def append_my_log(event: dict):
    """Append a signed event to local log, enforcing max size."""
    os.makedirs(os.path.dirname(MY_LOG_FILE), exist_ok=True)
    entries = load_my_log()
    entries.append(event)
    # Trim to max, keeping replaceable events (Kind 0, 3) always
    if len(entries) > MAX_LOG_ENTRIES:
        replaceable = [e for e in entries if e.get("kind") in (0, 3)]
        non_replaceable = [e for e in entries if e.get("kind") not in (0, 3)]
        non_replaceable = non_replaceable[-(MAX_LOG_ENTRIES - len(replaceable)):]
        entries = replaceable + non_replaceable
        entries.sort(key=lambda e: e.get("created_at", 0))
    with open(MY_LOG_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def github_token() -> str:
    """Get GitHub token from environment or config."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        cfg = load_config()
        token = cfg.get("mesh", {}).get("github_token", "")
    if not token:
        print("❌ GitHub token required. Set GITHUB_TOKEN env var or mesh.github_token in config.", file=sys.stderr)
        sys.exit(1)
    return token


def gist_api(url, method="GET", data=None, token=None):
    """GitHub Gist API request. Returns parsed JSON or None."""
    try:
        req = urllib.request.Request(url, method=method)
        if token:
            req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        body = None
        if data is not None:
            req.add_header("Content-Type", "application/json")
            body = json.dumps(data).encode()
        resp = urllib.request.urlopen(req, data=body, timeout=15)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        try:
            detail = json.loads(detail).get("message", detail)
        except Exception:
            pass
        print(f"⚠️  GitHub API {e.code}: {detail}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Request failed: {e}", file=sys.stderr)
    return None


def fetch_gist_file(gist_id, filename):
    """Fetch a specific file from a public Gist (no auth needed)."""
    # Use the Gist API to get file content — works for public gists without auth
    try:
        url = f"{GIST_API}/{gist_id}"
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        resp = urllib.request.urlopen(req, timeout=15)
        gist = json.loads(resp.read().decode())
        files = gist.get("files", {})
        if filename in files:
            return files[filename].get("content", "")
    except Exception:
        pass
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


def verify_event(event: dict) -> bool:
    """Verify an event's signature and ID."""
    try:
        expected = compute_id(
            event["pubkey"], event["created_at"],
            event["kind"], event["tags"], event["content"],
        )
        if event["id"] != expected:
            return False
        vk = nacl.signing.VerifyKey(bytes.fromhex(event["pubkey"]))
        vk.verify(bytes.fromhex(event["id"]), bytes.fromhex(event["sig"]))
        return True
    except Exception:
        return False


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


# ══════════════════════════════════════════════════════════════
# GIST OPERATIONS
# ══════════════════════════════════════════════════════════════


def create_agent_gist(token, profile_event, log_content=""):
    """Create a new public Gist for this agent."""
    data = {
        "description": "the-only mesh agent",
        "public": True,
        "files": {
            "profile.json": {"content": json.dumps(profile_event, indent=2, ensure_ascii=False)},
            "log.jsonl": {"content": log_content or ""},
            "follows.json": {"content": json.dumps([], indent=2)},
        },
    }
    return gist_api(GIST_API, method="POST", data=data, token=token)


def update_gist(gist_id, token, files):
    """Update specific files in a Gist. files = {filename: content_string}"""
    data = {"files": {name: {"content": content} for name, content in files.items()}}
    return gist_api(f"{GIST_API}/{gist_id}", method="PATCH", data=data, token=token)


def push_log_to_gist(gist_id, token):
    """Push the full local log to the agent's Gist."""
    entries = load_my_log()
    log_content = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    return update_gist(gist_id, token, {"log.jsonl": log_content})


# ══════════════════════════════════════════════════════════════
# TASTE MATCHING
# ══════════════════════════════════════════════════════════════


def taste_similarity(a: dict, b: dict) -> float:
    """Cosine similarity between two taste fingerprint dicts."""
    all_keys = set(a.keys()) | set(b.keys())
    if not all_keys:
        return 0.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in all_keys)
    mag_a = sum(v ** 2 for v in a.values()) ** 0.5
    mag_b = sum(v ** 2 for v in b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ══════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════


def action_init():
    """Generate identity, create Gist, seed from bootstrap."""
    cfg = load_config()
    token = github_token()

    # Check existing identity
    if os.path.exists(KEY_FILE):
        keys = load_json(KEY_FILE)
        if keys.get("private_key"):
            print(f"⚠️  Identity exists: {keys['public_key'][:16]}…")
            print("   Delete ~/memory/the_only_mycelium_key.json to re-init.")
            return

    # Generate keypair
    keys = generate_keypair()
    save_json(KEY_FILE, keys)
    print(f"🔑 Identity: {keys['public_key'][:16]}…")

    # Create profile event
    sk = load_signing_key()
    name = cfg.get("name", "Ruby")
    profile = json.dumps(
        {"name": name, "lang": "auto", "taste_fingerprint": {}, "version": "1.0.0"},
        ensure_ascii=False,
    )
    event = make_event(sk, 0, [], profile)

    # Store profile event in local log
    append_my_log(event)

    # Create Gist
    log_content = json.dumps(event, ensure_ascii=False)
    result = create_agent_gist(token, event, log_content=log_content)
    if not result:
        print("❌ Failed to create Gist. Check your GitHub token.", file=sys.stderr)
        sys.exit(1)

    gist_id = result["id"]
    print(f"📋 Gist created: {result['html_url']}")

    # Update config
    m = cfg.setdefault("mesh", {})
    m["enabled"] = True
    m["pubkey"] = keys["public_key"]
    m["gist_id"] = gist_id
    m["auto_publish_threshold"] = 7.5
    m["network_content_ratio"] = 0.2
    m["following"] = []
    m["allow_user_bridge"] = False
    save_config(cfg)

    # Load bootstrap peers
    if os.path.exists(BOOTSTRAP_FILE):
        bootstrap = load_json(BOOTSTRAP_FILE, {"peers": []})
        if bootstrap.get("peers"):
            peers_data = load_peers()
            for peer in bootstrap["peers"]:
                pk = peer.get("pubkey", "")
                if pk and pk != keys["public_key"]:
                    peers_data["peers"][pk] = {
                        "gist_id": peer.get("gist_id", ""),
                        "name": peer.get("name", ""),
                        "taste": peer.get("taste", {}),
                        "last_seen": 0,
                    }
            save_peers(peers_data)
            print(f"🌐 Loaded {len(bootstrap['peers'])} bootstrap peers.")

    print("✅ Mesh identity initialized.")


def action_publish(content_json, extra_tags=None, kind=1):
    """Publish a signed event to local log and push to Gist."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity. Run --action init first.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    token = github_token()
    gist_id = cfg.get("mesh", {}).get("gist_id", "")
    if not gist_id:
        print("❌ No Gist configured. Run --action init first.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(content_json)
    except json.JSONDecodeError:
        print("❌ Invalid JSON content.", file=sys.stderr)
        sys.exit(1)

    # Build tags
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
    if kind == 6 and "domain" in data:
        tags.append(["d", data["domain"]])
    if kind == 7 and "skill" in data:
        tags.append(["d", data["skill"]])

    event = make_event(sk, kind, tags, json.dumps(data, ensure_ascii=False))

    # Handle replaceable events (Kind 0, 3)
    if kind in (0, 3):
        entries = load_my_log()
        entries = [e for e in entries if e.get("kind") != kind]
        entries.append(event)
        with open(MY_LOG_FILE, "w") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    else:
        append_my_log(event)

    # Push to Gist
    if push_log_to_gist(gist_id, token):
        print(f"✅ Published (Kind {kind}): {event['id'][:16]}…")
    else:
        print("⚠️  Saved locally but Gist push failed. Will retry next sync.")


def action_sync():
    """Pull updates from followed agents. Output: JSON array of new content to stdout."""
    cfg = load_config()
    following = cfg.get("mesh", {}).get("following", [])
    peers_data = load_peers()
    os.makedirs(PEER_LOGS_DIR, exist_ok=True)

    new_content = []
    since = int(time.time()) - 48 * 3600  # Last 48 hours

    for pubkey in following:
        peer = peers_data.get("peers", {}).get(pubkey, {})
        gist_id = peer.get("gist_id", "")
        if not gist_id:
            continue

        # Fetch peer's log
        log_content = fetch_gist_file(gist_id, "log.jsonl")
        if not log_content:
            continue

        # Parse and verify events
        events = []
        for line in log_content.strip().split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if verify_event(event) and event.get("pubkey") == pubkey:
                    events.append(event)
            except (json.JSONDecodeError, KeyError):
                continue

        if not events:
            continue

        # Save to local peer log
        peer_log_file = os.path.join(PEER_LOGS_DIR, f"{pubkey[:16]}.jsonl")
        with open(peer_log_file, "w") as f:
            for e in events:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

        # Update peer last_seen
        latest_ts = max(e.get("created_at", 0) for e in events)
        if pubkey in peers_data.get("peers", {}):
            peers_data["peers"][pubkey]["last_seen"] = latest_ts

        # Also update peer profile if available
        profiles = [e for e in events if e.get("kind") == 0]
        if profiles:
            latest_profile = max(profiles, key=lambda e: e.get("created_at", 0))
            try:
                pdata = json.loads(latest_profile["content"])
                peers_data["peers"][pubkey]["name"] = pdata.get("name", "")
                peers_data["peers"][pubkey]["taste"] = pdata.get("taste_fingerprint", {})
            except (json.JSONDecodeError, KeyError):
                pass

        # Collect new content (Kind 1) from last 48h
        for e in events:
            if e.get("kind") == 1 and e.get("created_at", 0) >= since:
                new_content.append(e)

        # Gossip: read peer's follow list to discover new agents
        follows_content = fetch_gist_file(gist_id, "follows.json")
        if follows_content:
            try:
                peer_follows = json.loads(follows_content)
                for follow_entry in peer_follows:
                    fpk = follow_entry.get("pubkey", "") if isinstance(follow_entry, dict) else ""
                    fgist = follow_entry.get("gist_id", "") if isinstance(follow_entry, dict) else ""
                    if fpk and fpk not in peers_data.get("peers", {}) and fpk != cfg.get("mesh", {}).get("pubkey", ""):
                        peers_data["peers"][fpk] = {
                            "gist_id": fgist,
                            "name": follow_entry.get("name", "") if isinstance(follow_entry, dict) else "",
                            "taste": {},
                            "last_seen": 0,
                            "discovered_via": pubkey[:16],
                        }
            except (json.JSONDecodeError, TypeError):
                pass

    save_peers(peers_data)

    # Also push own log to Gist (ensure it's up to date)
    gist_id = cfg.get("mesh", {}).get("gist_id", "")
    if gist_id:
        token = github_token()
        push_log_to_gist(gist_id, token)

    # Sort by quality score descending
    def quality(e):
        for t in e.get("tags", []):
            if len(t) >= 2 and t[0] == "quality":
                try:
                    return float(t[1])
                except (ValueError, TypeError):
                    pass
        return 0.0

    new_content.sort(key=quality, reverse=True)
    print(json.dumps(new_content, ensure_ascii=False, indent=2))


def action_discover(limit=20):
    """Discover new agents through gossip and taste matching."""
    cfg = load_config()
    peers_data = load_peers()
    my_pubkey = cfg.get("mesh", {}).get("pubkey", "")

    # Get my taste fingerprint from context
    my_taste = {}
    try:
        my_log = load_my_log()
        my_profiles = [e for e in my_log if e.get("kind") == 0]
        if my_profiles:
            latest = max(my_profiles, key=lambda e: e.get("created_at", 0))
            pdata = json.loads(latest["content"])
            my_taste = pdata.get("taste_fingerprint", {})
    except Exception:
        pass

    # For each known peer (not yet followed), fetch their profile and compare taste
    following = set(cfg.get("mesh", {}).get("following", []))
    candidates = []

    for pubkey, peer in peers_data.get("peers", {}).items():
        if pubkey == my_pubkey or pubkey in following:
            continue

        gist_id = peer.get("gist_id", "")
        if not gist_id:
            continue

        # Fetch profile
        profile_content = fetch_gist_file(gist_id, "profile.json")
        if not profile_content:
            continue

        try:
            profile_event = json.loads(profile_content)
            if not verify_event(profile_event):
                continue
            pdata = json.loads(profile_event["content"])
            peer_taste = pdata.get("taste_fingerprint", {})
            name = pdata.get("name", "")

            # Update peer info
            peers_data["peers"][pubkey]["name"] = name
            peers_data["peers"][pubkey]["taste"] = peer_taste

            sim = taste_similarity(my_taste, peer_taste) if my_taste and peer_taste else 0.0
            candidates.append({
                "pubkey": pubkey,
                "gist_id": gist_id,
                "name": name,
                "taste": peer_taste,
                "similarity": round(sim, 3),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    save_peers(peers_data)

    # Sort by similarity
    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    candidates = candidates[:limit]

    print(json.dumps(candidates, ensure_ascii=False, indent=2))


def action_follow(target):
    """Follow an agent by pubkey."""
    cfg = load_config()
    m = cfg.setdefault("mesh", {})
    fl = m.setdefault("following", [])

    if target in fl:
        print(f"Already following {target[:16]}…")
        return

    fl.append(target)
    save_config(cfg)

    # Update follows.json on Gist
    gist_id = m.get("gist_id", "")
    if gist_id:
        token = github_token()
        peers_data = load_peers()
        follows_list = []
        for pk in fl:
            peer = peers_data.get("peers", {}).get(pk, {})
            follows_list.append({
                "pubkey": pk,
                "gist_id": peer.get("gist_id", ""),
                "name": peer.get("name", ""),
            })
        update_gist(gist_id, token, {"follows.json": json.dumps(follows_list, indent=2, ensure_ascii=False)})

    print(f"✅ Following {target[:16]}…")


def action_unfollow(target):
    """Unfollow an agent."""
    cfg = load_config()
    m = cfg.get("mesh", {})
    fl = m.get("following", [])

    if target not in fl:
        print(f"Not following {target[:16]}…")
        return

    fl.remove(target)
    m["following"] = fl
    save_config(cfg)

    # Update follows.json on Gist
    gist_id = m.get("gist_id", "")
    if gist_id:
        token = github_token()
        peers_data = load_peers()
        follows_list = []
        for pk in fl:
            peer = peers_data.get("peers", {}).get(pk, {})
            follows_list.append({
                "pubkey": pk,
                "gist_id": peer.get("gist_id", ""),
                "name": peer.get("name", ""),
            })
        update_gist(gist_id, token, {"follows.json": json.dumps(follows_list, indent=2, ensure_ascii=False)})

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
            "version": "1.0.0",
        },
        ensure_ascii=False,
    )
    event = make_event(sk, 0, [], profile)

    # Replace Kind 0 in local log
    entries = load_my_log()
    entries = [e for e in entries if e.get("kind") != 0]
    entries.append(event)
    with open(MY_LOG_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # Push to Gist
    gist_id = cfg.get("mesh", {}).get("gist_id", "")
    if gist_id:
        token = github_token()
        update_gist(gist_id, token, {
            "profile.json": json.dumps(event, indent=2, ensure_ascii=False),
        })
        push_log_to_gist(gist_id, token)
        print("✅ Profile updated.")
    else:
        print("⚠️  Profile saved locally but no Gist configured.")


def action_status():
    """Print mesh network status."""
    cfg = load_config()
    m = cfg.get("mesh", {})

    print("=== Mesh Network Status ===")
    print(f"Enabled:    {m.get('enabled', False)}")
    pk = m.get("pubkey", "")
    print(f"Public Key: {pk[:16]}…" if pk else "Public Key: (not set)")
    gist_id = m.get("gist_id", "")
    print(f"Gist ID:    {gist_id}" if gist_id else "Gist ID:    (not set)")
    print(f"Following:  {len(m.get('following', []))} agents")
    print(f"Publish threshold: {m.get('auto_publish_threshold', 7.5)}")
    print(f"Network ratio:     {m.get('network_content_ratio', 0.2)}")

    peers_data = load_peers()
    print(f"Known peers: {len(peers_data.get('peers', {}))}")

    if gist_id:
        result = gist_api(f"{GIST_API}/{gist_id}")
        if result:
            print(f"\n📋 Gist: ✅ {result.get('html_url', '')}")
        else:
            print("\n📋 Gist: ❌ Unreachable")

    my_log = load_my_log()
    kind_counts = {}
    for e in my_log:
        k = e.get("kind", -1)
        kind_counts[k] = kind_counts.get(k, 0) + 1
    if kind_counts:
        print(f"\nLocal log: {len(my_log)} events")
        for k, c in sorted(kind_counts.items()):
            names = {0: "Profile", 1: "Content", 2: "Boost", 3: "Follows", 5: "Feedback", 6: "Source Rec", 7: "Capability Rec"}
            print(f"  Kind {k} ({names.get(k, '?')}): {c}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════


def main():
    p = argparse.ArgumentParser(description="Mesh Sync — the_only P2P network")
    p.add_argument(
        "--action",
        required=True,
        choices=["init", "publish", "sync", "discover", "follow", "unfollow", "profile_update", "status"],
    )
    p.add_argument("--content", help="JSON content string (for publish)")
    p.add_argument("--tags", help="Extra comma-separated tags (for publish)")
    p.add_argument("--kind", type=int, default=1, help="Event kind (1=content, 6=source rec, 7=capability rec)")
    p.add_argument("--target", help="Pubkey (for follow/unfollow)")
    p.add_argument("--taste", help="Taste fingerprint JSON (for profile_update)")
    p.add_argument("--limit", type=int, default=20)

    args = p.parse_args()

    if args.action == "init":
        action_init()
    elif args.action == "publish":
        if not args.content:
            print("❌ --content required for publish.", file=sys.stderr)
            sys.exit(1)
        action_publish(args.content, extra_tags=args.tags, kind=args.kind)
    elif args.action == "sync":
        action_sync()
    elif args.action == "discover":
        action_discover(limit=args.limit)
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
