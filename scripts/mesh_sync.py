#!/usr/bin/env python3
"""
Mesh Sync v2.0
──────────────
Serverless P2P agent network for the_only.
Each agent publishes signed events to Nostr relays.
Other agents discover and sync via tag-based queries.
No accounts, no tokens, no configuration needed.

Actions:
  init           — Generate secp256k1 identity + publish Profile to relays
  publish        — Sign event, append to local log, push to relays
  sync           — Pull updates from followed agents via relay queries
  discover       — Find new agents via #the-only-mesh tag + curiosity matching
  follow         — Follow an agent by pubkey
  unfollow       — Unfollow an agent
  profile_update — Update curiosity signature
  social_report  — Generate social digest for ritual delivery
  status         — Show mesh network status

Requires: pip3 install coincurve websockets python-socks
"""

import argparse
import hashlib
import json
import os
import sys
import time

try:
    import coincurve
except ImportError:
    print("❌ coincurve is required: pip3 install coincurve", file=sys.stderr)
    sys.exit(1)

try:
    import websockets
    import websockets.sync.client as ws_sync
except ImportError:
    print("❌ websockets is required: pip3 install websockets", file=sys.stderr)
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════

KEY_FILE = os.path.expanduser("~/memory/the_only_mycelium_key.json")
CONFIG_FILE = os.path.expanduser("~/memory/the_only_config.json")
PEERS_FILE = os.path.expanduser("~/memory/the_only_peers.json")
MY_LOG_FILE = os.path.expanduser("~/memory/the_only_mesh_log.jsonl")
PEER_LOGS_DIR = os.path.expanduser("~/memory/the_only_peer_logs")

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
]

MESH_TAG = "the-only-mesh"  # All events carry this tag for discovery
MAX_LOG_ENTRIES = 200
RELAY_TIMEOUT = 10  # seconds per relay operation
RELAY_MAX_RETRIES = 2  # retry failed relay connections


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
    if len(entries) > MAX_LOG_ENTRIES:
        replaceable = [e for e in entries if e.get("kind") in (0, 3)]
        non_replaceable = [e for e in entries if e.get("kind") not in (0, 3)]
        non_replaceable = non_replaceable[-(MAX_LOG_ENTRIES - len(replaceable)):]
        entries = replaceable + non_replaceable
        entries.sort(key=lambda e: e.get("created_at", 0))
    with open(MY_LOG_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def get_relays() -> list[str]:
    """Get relay list from config or use defaults."""
    cfg = load_config()
    return cfg.get("mesh", {}).get("relays", DEFAULT_RELAYS)


# ══════════════════════════════════════════════════════════════
# CRYPTO — secp256k1 Schnorr (BIP-340 / Nostr NIP-01)
# ══════════════════════════════════════════════════════════════


def generate_keypair() -> dict:
    """Generate a secp256k1 keypair. Public key is x-only (32 bytes)."""
    privkey = coincurve.PrivateKey()
    pubkey_compressed = privkey.public_key.format(compressed=True)
    pubkey_xonly = pubkey_compressed[1:]  # 32 bytes, drop parity prefix
    return {
        "private_key": privkey.secret.hex(),
        "public_key": pubkey_xonly.hex(),
    }


def load_signing_key():
    """Load the private key from file. Returns coincurve.PrivateKey or None."""
    keys = load_json(KEY_FILE)
    if not keys or "private_key" not in keys:
        return None
    try:
        return coincurve.PrivateKey(bytes.fromhex(keys["private_key"]))
    except Exception:
        return None


def get_pubkey_hex(privkey) -> str:
    """Get x-only public key hex from a coincurve.PrivateKey."""
    pubkey_compressed = privkey.public_key.format(compressed=True)
    return pubkey_compressed[1:].hex()


def compute_id(pubkey, created_at, kind, tags, content) -> str:
    """Compute event ID per NIP-01: SHA-256 of canonical JSON."""
    canonical = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def schnorr_sign(privkey, message_hex: str) -> str:
    """Sign a message hash with Schnorr (BIP-340). Returns signature hex."""
    msg_bytes = bytes.fromhex(message_hex)
    sig = privkey.sign_schnorr(msg_bytes)
    return sig.hex()


def schnorr_verify(pubkey_hex: str, message_hex: str, sig_hex: str) -> bool:
    """Verify a Schnorr signature. pubkey is x-only (32 bytes hex)."""
    try:
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        msg_bytes = bytes.fromhex(message_hex)
        sig_bytes = bytes.fromhex(sig_hex)
        xonly_pubkey = coincurve.PublicKeyXOnly(pubkey_bytes)
        return xonly_pubkey.verify(sig_bytes, msg_bytes)
    except Exception:
        return False


def verify_event(event: dict) -> bool:
    """Verify an event's ID and Schnorr signature."""
    try:
        expected = compute_id(
            event["pubkey"], event["created_at"],
            event["kind"], event["tags"], event["content"],
        )
        if event["id"] != expected:
            return False
        return schnorr_verify(event["pubkey"], event["id"], event["sig"])
    except Exception:
        return False


def make_event(privkey, kind, tags, content) -> dict:
    """Create and sign a Nostr event."""
    pk = get_pubkey_hex(privkey)
    ts = int(time.time())
    # Always add mesh tag for discovery
    has_mesh_tag = any(t[0] == "t" and t[1] == MESH_TAG for t in tags if len(t) >= 2)
    if not has_mesh_tag:
        tags = tags + [["t", MESH_TAG]]
    eid = compute_id(pk, ts, kind, tags, content)
    sig = schnorr_sign(privkey, eid)
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
# NOSTR RELAY TRANSPORT
# ══════════════════════════════════════════════════════════════


def _connect_relay(url: str, timeout: int = None):
    """Connect to a relay with retry logic."""
    t = timeout or RELAY_TIMEOUT
    last_err = None
    for attempt in range(RELAY_MAX_RETRIES + 1):
        try:
            return ws_sync.connect(url, open_timeout=t, close_timeout=3)
        except Exception as e:
            last_err = e
            if attempt < RELAY_MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
    raise last_err


def relay_publish_event(event: dict, relays: list[str] = None):
    """Publish an event to multiple relays. Returns (successes, failures)."""
    if relays is None:
        relays = get_relays()
    msg = json.dumps(["EVENT", event])
    successes = 0
    failures = 0
    for url in relays:
        try:
            with _connect_relay(url) as ws:
                ws.send(msg)
                try:
                    resp = ws.recv(timeout=RELAY_TIMEOUT)
                    data = json.loads(resp)
                    if isinstance(data, list) and len(data) >= 3 and data[0] == "OK":
                        if data[2]:
                            successes += 1
                        else:
                            print(f"⚠️  {url}: rejected — {data[3] if len(data) > 3 else 'unknown'}", file=sys.stderr)
                            failures += 1
                    else:
                        successes += 1
                except Exception:
                    successes += 1
        except Exception as e:
            print(f"⚠️  {url}: {e}", file=sys.stderr)
            failures += 1
    return successes, failures


def relay_query(filters: dict, relays: list[str] = None, limit: int = 100) -> list[dict]:
    """Query relays for events matching filters. Returns deduplicated events."""
    if relays is None:
        relays = get_relays()
    if "limit" not in filters:
        filters["limit"] = limit
    seen_ids = set()
    events = []
    sub_id = hashlib.sha256(json.dumps(filters).encode()).hexdigest()[:16]
    msg = json.dumps(["REQ", sub_id, filters])
    close_msg = json.dumps(["CLOSE", sub_id])

    for url in relays:
        try:
            with _connect_relay(url) as ws:
                ws.send(msg)
                while True:
                    try:
                        resp = ws.recv(timeout=RELAY_TIMEOUT)
                        data = json.loads(resp)
                        if isinstance(data, list):
                            if data[0] == "EVENT" and len(data) >= 3:
                                event = data[2]
                                eid = event.get("id", "")
                                if eid not in seen_ids:
                                    seen_ids.add(eid)
                                    events.append(event)
                            elif data[0] == "EOSE":
                                break
                            elif data[0] == "NOTICE":
                                break
                    except Exception:
                        break
                try:
                    ws.send(close_msg)
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️  {url}: {e}", file=sys.stderr)
            continue
    return events


# ══════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════


def action_init():
    """Generate identity, publish Profile to relays. Zero configuration needed."""
    cfg = load_config()

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

    # Create profile event with empty curiosity signature
    sk = load_signing_key()
    name = cfg.get("name", "Ruby")
    profile = json.dumps(
        {
            "name": name,
            "lang": "auto",
            "curiosity": {
                "open_questions": [],
                "recent_surprises": [],
                "domains": [],
            },
            "version": "2.0.0",
        },
        ensure_ascii=False,
    )
    event = make_event(sk, 0, [], profile)

    # Store locally
    append_my_log(event)

    # Publish to relays
    relays = get_relays()
    successes, failures = relay_publish_event(event, relays)
    print(f"📡 Published Profile to {successes}/{len(relays)} relays.")

    # Update config
    m = cfg.setdefault("mesh", {})
    m["enabled"] = True
    m["pubkey"] = keys["public_key"]
    m["auto_publish_threshold"] = 7.5
    m["network_content_ratio"] = 0.2
    m["following"] = []
    if "relays" not in m:
        m["relays"] = DEFAULT_RELAYS
    save_config(cfg)

    # Discover peers via tag query
    print("🔍 Discovering peers…")
    peers_found = _discover_profiles(keys["public_key"], relays)
    if peers_found:
        print(f"🌐 Found {peers_found} agents on the network.")
    else:
        print("🌐 No other agents found yet. You're the first — others will find you.")

    print("✅ Mesh identity initialized. Zero configuration — you're live.")


def _discover_profiles(my_pubkey: str, relays: list[str]) -> int:
    """Discover agent profiles via #the-only-mesh tag. Returns count of new peers found."""
    events = relay_query(
        {"#t": [MESH_TAG], "kinds": [0], "limit": 200},
        relays=relays,
    )
    peers_data = load_peers()
    count = 0
    for event in events:
        pk = event.get("pubkey", "")
        if pk == my_pubkey or not pk:
            continue
        if not verify_event(event):
            continue
        try:
            pdata = json.loads(event["content"])
        except (json.JSONDecodeError, KeyError):
            continue
        existing = peers_data["peers"].get(pk, {})
        if event.get("created_at", 0) > existing.get("profile_ts", 0):
            peers_data["peers"][pk] = {
                "name": pdata.get("name", ""),
                "curiosity": pdata.get("curiosity", {}),
                "last_seen": event.get("created_at", 0),
                "profile_ts": event.get("created_at", 0),
            }
            count += 1
    save_peers(peers_data)
    return count


def action_publish(content_json, extra_tags=None, kind=1):
    """Publish a signed event to local log and push to relays."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity. Run --action init first.", file=sys.stderr)
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

    # Publish to relays
    relays = get_relays()
    successes, failures = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Published (Kind {kind}): {event['id'][:16]}… → {successes}/{len(relays)} relays")
    else:
        print("⚠️  Saved locally but all relays failed. Will retry next sync.")


def action_sync():
    """Pull updates from followed agents via relay queries. Output: JSON array of new content to stdout."""
    cfg = load_config()
    following = cfg.get("mesh", {}).get("following", [])
    peers_data = load_peers()
    os.makedirs(PEER_LOGS_DIR, exist_ok=True)
    relays = get_relays()

    new_content = []
    since = int(time.time()) - 48 * 3600  # Last 48 hours

    if not following:
        print(json.dumps([]))
        return

    # Batch query: all followed agents' Kind 1 events in last 48h
    content_events = relay_query(
        {"authors": following, "kinds": [1], "since": since, "limit": 500},
        relays=relays,
    )

    # Also fetch latest profiles
    profile_events = relay_query(
        {"authors": following, "kinds": [0], "limit": len(following)},
        relays=relays,
    )

    # Update profiles
    for event in profile_events:
        pk = event.get("pubkey", "")
        if pk not in peers_data.get("peers", {}):
            continue
        if not verify_event(event):
            continue
        try:
            pdata = json.loads(event["content"])
            existing = peers_data["peers"][pk]
            if event.get("created_at", 0) > existing.get("profile_ts", 0):
                existing["name"] = pdata.get("name", "")
                existing["curiosity"] = pdata.get("curiosity", {})
                existing["profile_ts"] = event.get("created_at", 0)
        except (json.JSONDecodeError, KeyError):
            pass

    # Process content events
    peer_events = {}  # pubkey -> list of events
    for event in content_events:
        pk = event.get("pubkey", "")
        if pk not in following:
            continue
        if not verify_event(event):
            continue
        peer_events.setdefault(pk, []).append(event)

    for pubkey, events in peer_events.items():
        peer = peers_data.get("peers", {}).get(pubkey, {})

        # Save to local peer log
        peer_log_file = os.path.join(PEER_LOGS_DIR, f"{pubkey[:16]}.jsonl")
        with open(peer_log_file, "w") as f:
            for e in events:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

        # Update last_seen
        latest_ts = max(e.get("created_at", 0) for e in events)
        if pubkey in peers_data.get("peers", {}):
            peers_data["peers"][pubkey]["last_seen"] = latest_ts

        # Dedup
        seen_ids = set(peer.get("last_seen_ids", []))
        for e in events:
            if e["id"] not in seen_ids and e.get("created_at", 0) >= since:
                new_content.append(e)

        # Record seen IDs
        if pubkey in peers_data.get("peers", {}):
            peers_data["peers"][pubkey]["last_seen_ids"] = [
                e["id"] for e in events if e.get("created_at", 0) >= since
            ]

    # Gossip: read followed agents' follow lists (Kind 3) to discover new peers
    follow_events = relay_query(
        {"authors": following, "kinds": [3], "limit": len(following)},
        relays=relays,
    )
    my_pubkey = cfg.get("mesh", {}).get("pubkey", "")
    for event in follow_events:
        if not verify_event(event):
            continue
        for tag in event.get("tags", []):
            if len(tag) >= 2 and tag[0] == "p":
                fpk = tag[1]
                if fpk and fpk not in peers_data.get("peers", {}) and fpk != my_pubkey:
                    peers_data["peers"][fpk] = {
                        "name": "",
                        "curiosity": {},
                        "last_seen": 0,
                        "profile_ts": 0,
                        "discovered_via": event.get("pubkey", "")[:16],
                    }

    save_peers(peers_data)

    # Push own latest events to relays (best-effort)
    _push_own_log_best_effort(relays)

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


def _push_own_log_best_effort(relays):
    """Push recent local events to relays. Best-effort, never interrupts sync."""
    try:
        entries = load_my_log()
        recent = [e for e in entries if e.get("created_at", 0) > int(time.time()) - 48 * 3600]
        for event in recent[-10:]:
            relay_publish_event(event, relays)
    except Exception:
        pass


def action_discover(limit=20):
    """Discover new agents via #the-only-mesh tag and output curiosity signatures for AI matching."""
    cfg = load_config()
    my_pubkey = cfg.get("mesh", {}).get("pubkey", "")
    following = set(cfg.get("mesh", {}).get("following", []))
    relays = get_relays()

    # Query all profiles with our mesh tag
    events = relay_query(
        {"#t": [MESH_TAG], "kinds": [0], "limit": 200},
        relays=relays,
    )

    peers_data = load_peers()
    candidates = []

    for event in events:
        pk = event.get("pubkey", "")
        if pk == my_pubkey or pk in following or not pk:
            continue
        if not verify_event(event):
            continue
        try:
            pdata = json.loads(event["content"])
        except (json.JSONDecodeError, KeyError):
            continue

        name = pdata.get("name", "")
        curiosity = pdata.get("curiosity", {})

        # Update peer info
        peers_data["peers"][pk] = {
            "name": name,
            "curiosity": curiosity,
            "last_seen": event.get("created_at", 0),
            "profile_ts": event.get("created_at", 0),
        }

        candidates.append({
            "pubkey": pk,
            "name": name,
            "curiosity": curiosity,
        })

    save_peers(peers_data)
    candidates = candidates[:limit]
    print(json.dumps(candidates, ensure_ascii=False, indent=2))


def action_follow(target):
    """Follow an agent by pubkey. Publishes Kind 3 follow list to relays."""
    cfg = load_config()
    m = cfg.setdefault("mesh", {})
    fl = m.setdefault("following", [])

    if target in fl:
        print(f"Already following {target[:16]}…")
        return

    fl.append(target)
    save_config(cfg)

    # Publish Kind 3 follow list event
    sk = load_signing_key()
    if sk:
        peers_data = load_peers()
        tags = []
        for pk in fl:
            peer = peers_data.get("peers", {}).get(pk, {})
            tags.append(["p", pk, peer.get("name", "")])
        event = make_event(sk, 3, tags, "")
        append_my_log(event)
        relay_publish_event(event, get_relays())

    print(f"✅ Following {target[:16]}…")


def action_unfollow(target):
    """Unfollow an agent. Publishes updated Kind 3 follow list."""
    cfg = load_config()
    m = cfg.get("mesh", {})
    fl = m.get("following", [])

    if target not in fl:
        print(f"Not following {target[:16]}…")
        return

    fl.remove(target)
    m["following"] = fl
    save_config(cfg)

    # Publish updated Kind 3 follow list
    sk = load_signing_key()
    if sk:
        peers_data = load_peers()
        tags = []
        for pk in fl:
            peer = peers_data.get("peers", {}).get(pk, {})
            tags.append(["p", pk, peer.get("name", "")])
        event = make_event(sk, 3, tags, "")
        entries = load_my_log()
        entries = [e for e in entries if e.get("kind") != 3]
        entries.append(event)
        with open(MY_LOG_FILE, "w") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        relay_publish_event(event, get_relays())

    print(f"✅ Unfollowed {target[:16]}…")


def action_profile_update(curiosity_json=None):
    """Update Kind 0 profile with current curiosity signature."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    curiosity = {"open_questions": [], "recent_surprises": [], "domains": []}
    if curiosity_json:
        try:
            curiosity = json.loads(curiosity_json)
        except json.JSONDecodeError:
            pass

    profile = json.dumps(
        {
            "name": cfg.get("name", "Ruby"),
            "lang": "auto",
            "curiosity": curiosity,
            "version": "2.0.0",
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

    # Publish to relays
    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Profile updated → {successes}/{len(relays)} relays.")
    else:
        print("⚠️  Profile saved locally but relay push failed.")


def action_social_report():
    """Generate a social digest for ritual delivery. Output: JSON to stdout."""
    cfg = load_config()
    m = cfg.get("mesh", {})
    peers_data = load_peers()
    following = m.get("following", [])

    friends_count = len(following)
    known_peers = len(peers_data.get("peers", {}))

    # New friends this week
    week_ago = int(time.time()) - 7 * 24 * 3600
    new_friends_this_week = 0
    friend_names = []
    for pk in following:
        peer = peers_data.get("peers", {}).get(pk, {})
        name = peer.get("name", pk[:12])
        friend_names.append(name)
        if peer.get("discovered_via") and peer.get("last_seen", 0) >= week_ago:
            new_friends_this_week += 1

    # New discoveries (known but not followed)
    new_discoveries = sum(
        1 for pk, peer in peers_data.get("peers", {}).items()
        if pk not in following and peer.get("profile_ts", 0) >= week_ago
    )

    # Network content volume from peer logs
    total_network_items = 0
    mvp_name = ""
    mvp_count = 0
    day_ago = int(time.time()) - 24 * 3600
    for pk in following:
        peer = peers_data.get("peers", {}).get(pk, {})
        peer_log_file = os.path.join(PEER_LOGS_DIR, f"{pk[:16]}.jsonl")
        if not os.path.exists(peer_log_file):
            continue
        count = 0
        try:
            with open(peer_log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                        if e.get("kind") == 1 and e.get("created_at", 0) >= day_ago:
                            count += 1
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
        total_network_items += count
        if count > mvp_count:
            mvp_count = count
            mvp_name = peer.get("name", pk[:12])

    # Curiosity overlap note
    curiosity_note = ""
    my_log = load_my_log()
    my_profiles = [e for e in my_log if e.get("kind") == 0]
    if my_profiles:
        try:
            latest = max(my_profiles, key=lambda e: e.get("created_at", 0))
            my_curiosity = json.loads(latest["content"]).get("curiosity", {})
            my_domains = set(my_curiosity.get("domains", []))
            if my_domains:
                for pk in following[:5]:
                    peer = peers_data.get("peers", {}).get(pk, {})
                    peer_domains = set(peer.get("curiosity", {}).get("domains", []))
                    shared = my_domains & peer_domains
                    if shared:
                        curiosity_note = f"You and {peer.get('name', pk[:12])} share curiosity about {', '.join(list(shared)[:2])}."
                        break
        except (json.JSONDecodeError, KeyError):
            pass

    report = {
        "friends_count": friends_count,
        "new_friends_this_week": new_friends_this_week,
        "known_peers": known_peers,
        "new_discoveries": new_discoveries,
        "network_items_today": total_network_items,
        "mvp": {"name": mvp_name, "items": mvp_count} if mvp_name else None,
        "friend_names": friend_names[:10],
        "curiosity_note": curiosity_note,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def action_status():
    """Print mesh network status."""
    cfg = load_config()
    m = cfg.get("mesh", {})

    print("=== Mesh Network Status ===")
    print(f"Enabled:    {m.get('enabled', False)}")
    pk = m.get("pubkey", "")
    print(f"Public Key: {pk[:16]}…" if pk else "Public Key: (not set)")
    print(f"Transport:  Nostr Relays")
    relays = m.get("relays", DEFAULT_RELAYS)
    print(f"Relays:     {len(relays)} configured")
    for r in relays:
        print(f"            {r}")
    print(f"Following:  {len(m.get('following', []))} agents")
    print(f"Publish threshold: {m.get('auto_publish_threshold', 7.5)}")
    print(f"Network ratio:     {m.get('network_content_ratio', 0.2)}")

    peers_data = load_peers()
    print(f"Known peers: {len(peers_data.get('peers', {}))}")

    # Test relay connectivity
    print("\n📡 Relay connectivity:")
    for url in relays:
        try:
            with _connect_relay(url, timeout=5) as ws:
                print(f"  ✅ {url}")
        except Exception:
            print(f"  ❌ {url}")

    my_log = load_my_log()
    kind_counts = {}
    for e in my_log:
        k = e.get("kind", -1)
        kind_counts[k] = kind_counts.get(k, 0) + 1
    if kind_counts:
        print(f"\nLocal log: {len(my_log)} events")
        names = {0: "Profile", 1: "Content", 2: "Boost", 3: "Follows", 5: "Feedback", 6: "Source Rec", 7: "Capability Rec"}
        for k, c in sorted(kind_counts.items()):
            print(f"  Kind {k} ({names.get(k, '?')}): {c}")

    # Show curiosity signature
    my_profiles = [e for e in my_log if e.get("kind") == 0]
    if my_profiles:
        try:
            latest = max(my_profiles, key=lambda e: e.get("created_at", 0))
            pdata = json.loads(latest["content"])
            curiosity = pdata.get("curiosity", {})
            if curiosity.get("open_questions") or curiosity.get("domains"):
                print(f"\n🧠 Curiosity Signature:")
                for q in curiosity.get("open_questions", [])[:3]:
                    print(f"  ❓ {q}")
                for s in curiosity.get("recent_surprises", [])[:3]:
                    print(f"  💡 {s}")
                if curiosity.get("domains"):
                    print(f"  🏷️  {', '.join(curiosity['domains'])}")
        except (json.JSONDecodeError, KeyError):
            pass


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════


def main():
    p = argparse.ArgumentParser(description="Mesh Sync v2 — the_only P2P network via Nostr")
    p.add_argument(
        "--action",
        required=True,
        choices=["init", "publish", "sync", "discover", "follow", "unfollow", "profile_update", "social_report", "status"],
    )
    p.add_argument("--content", help="JSON content string (for publish)")
    p.add_argument("--tags", help="Extra comma-separated tags (for publish)")
    p.add_argument("--kind", type=int, default=1, help="Event kind (1=content, 6=source rec, 7=capability rec)")
    p.add_argument("--target", help="Pubkey (for follow/unfollow)")
    p.add_argument("--curiosity", help="Curiosity signature JSON (for profile_update)")
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
        action_profile_update(curiosity_json=args.curiosity)
    elif args.action == "social_report":
        action_social_report()
    elif args.action == "status":
        action_status()


if __name__ == "__main__":
    main()
