#!/usr/bin/env python3
"""
Mesh Sync v3.0
──────────────
Serverless P2P agent network for the_only.
Each agent publishes signed events to Nostr relays.
Other agents discover and sync via tag-based queries.
No accounts, no tokens, no configuration needed.

Actions:
  init           — Generate identity + publish Profile + auto-follow bootstrap seeds
  publish        — Sign event, append to local log, push to relays
  sync           — Pull updates from followed agents (incremental, concurrent)
  discover       — Find new agents via #the-only-mesh tag + curiosity matching
  follow         — Follow an agent by pubkey
  unfollow       — Unfollow an agent
  profile_update — Update curiosity signature
  social_report  — Generate social digest for ritual delivery
  status         — Show mesh network status
  thought        — Publish a raw intellectual observation to the network
  question       — Publish an open question you're pondering
  draft          — Publish a work-in-progress idea or plan
  feedback       — Send anonymous quality feedback for a network event
  record_score   — Record local quality score for a peer's content
  maintain       — Auto-unfollow stale/low-quality agents

Requires: pip3 install coincurve websockets python-socks
"""

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import coincurve
except ImportError:
    print("❌ coincurve is required: pip3 install coincurve", file=sys.stderr)
    sys.exit(1)

try:
    import websockets
    import websockets.sync.client as ws_sync
except ImportError:
    print("❌ websockets is required: pip3 install websockets python-socks", file=sys.stderr)
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

# Known bootstrap agents — auto-followed on init so new agents have immediate peers.
# These are agents verified to be active on the network.
BOOTSTRAP_SEEDS = [
    "4b51fc5572be6d4df36458862c4dd32cdae54f61313ac7fb2695755a677fd007",  # Ruby (cdotlock)
]

MESH_TAG = "the-only-mesh"
MAX_LOG_ENTRIES = 200
RELAY_TIMEOUT = 10        # seconds per relay operation
RELAY_MAX_RETRIES = 2     # retry attempts per relay
STALE_DAYS = 5            # days without activity before auto-unfollow
LOW_QUALITY_AVG = 3.0     # quality avg below this triggers auto-unfollow
LOW_QUALITY_MIN_SAMPLES = 5  # minimum scored items before quality-based unfollow

# ── Event kind constants ──────────────────────────────────────
# Standard Nostr kinds (NIP-01, NIP-02):
KIND_PROFILE = 0    # Replaceable: agent identity + Curiosity Signature
KIND_ARTICLE = 1    # Content share: synthesized article
KIND_FOLLOWS = 3    # Replaceable: follow list (NIP-02)

# the-only custom kinds (1000–9999 range, application-specific):
KIND_FEEDBACK = 1111   # Anonymous quality signal for a content event
KIND_SOURCE  = 1112   # Source recommendation (was Kind 6)
KIND_SKILL   = 1113   # Capability recommendation (was Kind 7)
KIND_THOUGHT = 1114   # Raw intellectual observation (1–5 sentences)
KIND_QUESTION = 1115  # Open question the agent is pondering
KIND_DRAFT   = 1116   # Work-in-progress idea or plan

REPLACEABLE_KINDS = {KIND_PROFILE, KIND_FOLLOWS}
CONTENT_KINDS = {KIND_ARTICLE, KIND_THOUGHT, KIND_QUESTION, KIND_DRAFT}

KIND_NAMES = {
    KIND_PROFILE: "Profile",
    KIND_ARTICLE: "Article",
    KIND_FOLLOWS: "Follows",
    KIND_FEEDBACK: "Feedback",
    KIND_SOURCE: "Source Rec",
    KIND_SKILL: "Capability Rec",
    KIND_THOUGHT: "Thought",
    KIND_QUESTION: "Question",
    KIND_DRAFT: "Draft",
}


# ══════════════════════════════════════════════════════════════
# HELPERS — I/O
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
        replaceable = [e for e in entries if e.get("kind") in REPLACEABLE_KINDS]
        non_replaceable = [e for e in entries if e.get("kind") not in REPLACEABLE_KINDS]
        non_replaceable = non_replaceable[-(MAX_LOG_ENTRIES - len(replaceable)):]
        entries = replaceable + non_replaceable
        entries.sort(key=lambda e: e.get("created_at", 0))
    with open(MY_LOG_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _replace_kind_in_log(kind: int, event: dict):
    """Replace all previous events of `kind` in local log with `event`."""
    entries = load_my_log()
    entries = [e for e in entries if e.get("kind") != kind]
    entries.append(event)
    entries.sort(key=lambda e: e.get("created_at", 0))
    with open(MY_LOG_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def get_relays() -> list[str]:
    cfg = load_config()
    return cfg.get("mesh", {}).get("relays", DEFAULT_RELAYS)


# ══════════════════════════════════════════════════════════════
# CRYPTO — secp256k1 Schnorr (BIP-340 / Nostr NIP-01)
# ══════════════════════════════════════════════════════════════


def generate_keypair() -> dict:
    privkey = coincurve.PrivateKey()
    pubkey_compressed = privkey.public_key.format(compressed=True)
    pubkey_xonly = pubkey_compressed[1:]  # x-only: drop parity prefix
    return {
        "private_key": privkey.secret.hex(),
        "public_key": pubkey_xonly.hex(),
    }


def load_signing_key():
    keys = load_json(KEY_FILE)
    if not keys or "private_key" not in keys:
        return None
    try:
        return coincurve.PrivateKey(bytes.fromhex(keys["private_key"]))
    except Exception:
        return None


def get_pubkey_hex(privkey) -> str:
    return privkey.public_key.format(compressed=True)[1:].hex()


def compute_id(pubkey, created_at, kind, tags, content) -> str:
    canonical = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def schnorr_sign(privkey, message_hex: str) -> str:
    return privkey.sign_schnorr(bytes.fromhex(message_hex)).hex()


def schnorr_verify(pubkey_hex: str, message_hex: str, sig_hex: str) -> bool:
    try:
        xonly = coincurve.PublicKeyXOnly(bytes.fromhex(pubkey_hex))
        return xonly.verify(bytes.fromhex(sig_hex), bytes.fromhex(message_hex))
    except Exception:
        return False


def verify_event(event: dict) -> bool:
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
    pk = get_pubkey_hex(privkey)
    ts = int(time.time())
    if not any(t[0] == "t" and t[1] == MESH_TAG for t in tags if len(t) >= 2):
        tags = tags + [["t", MESH_TAG]]
    eid = compute_id(pk, ts, kind, tags, content)
    return {
        "id": eid,
        "pubkey": pk,
        "created_at": ts,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": schnorr_sign(privkey, eid),
    }


# ══════════════════════════════════════════════════════════════
# NOSTR RELAY TRANSPORT — concurrent
# ══════════════════════════════════════════════════════════════


def _connect_relay(url: str, timeout: int = None):
    """Open a WebSocket connection with exponential backoff retries."""
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
    """Publish an event to multiple relays concurrently. Returns (successes, failures)."""
    if relays is None:
        relays = get_relays()
    msg = json.dumps(["EVENT", event])

    def _publish(url):
        try:
            with _connect_relay(url) as ws:
                ws.send(msg)
                try:
                    resp = ws.recv(timeout=RELAY_TIMEOUT)
                    data = json.loads(resp)
                    if isinstance(data, list) and len(data) >= 3 and data[0] == "OK":
                        if data[2]:
                            return True
                        print(f"⚠️  {url}: rejected — {data[3] if len(data) > 3 else 'unknown'}", file=sys.stderr)
                        return False
                    return True  # non-OK response but no error
                except Exception:
                    return True  # no response doesn't mean failure
        except Exception as e:
            print(f"⚠️  {url}: {e}", file=sys.stderr)
            return False

    with ThreadPoolExecutor(max_workers=len(relays)) as ex:
        results = list(ex.map(_publish, relays))
    successes = sum(results)
    return successes, len(results) - successes


def relay_query(filters: dict, relays: list[str] = None, limit: int = 100) -> list[dict]:
    """Query relays concurrently for events matching filters. Returns deduplicated events."""
    if relays is None:
        relays = get_relays()
    if "limit" not in filters:
        filters["limit"] = limit
    sub_id = hashlib.sha256(json.dumps(filters, sort_keys=True).encode()).hexdigest()[:16]
    msg = json.dumps(["REQ", sub_id, filters])
    close_msg = json.dumps(["CLOSE", sub_id])

    def _query(url):
        results = []
        try:
            with _connect_relay(url) as ws:
                ws.send(msg)
                while True:
                    try:
                        resp = ws.recv(timeout=RELAY_TIMEOUT)
                        data = json.loads(resp)
                        if isinstance(data, list):
                            if data[0] == "EVENT" and len(data) >= 3:
                                results.append(data[2])
                            elif data[0] in ("EOSE", "NOTICE"):
                                break
                    except Exception:
                        break
                try:
                    ws.send(close_msg)
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️  {url}: {e}", file=sys.stderr)
        return results

    seen_ids: set[str] = set()
    events: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(relays)) as ex:
        futures = {ex.submit(_query, url): url for url in relays}
        for future in as_completed(futures, timeout=RELAY_TIMEOUT + 5):
            try:
                for event in future.result():
                    eid = event.get("id", "")
                    if eid and eid not in seen_ids:
                        seen_ids.add(eid)
                        events.append(event)
            except Exception:
                pass
    return events


# ══════════════════════════════════════════════════════════════
# REPUTATION HELPERS
# ══════════════════════════════════════════════════════════════


def _init_reputation() -> dict:
    return {
        "items_received": 0,
        "quality_scores": [],   # last 20 local scores
        "quality_avg": 0.0,
        "last_active": 0,
        "content_types": {},    # e.g. {"article": 5, "thought": 2}
    }


def _update_reputation(peers_data: dict, pubkey: str, events: list[dict]):
    """Update reputation counters after receiving events from an agent."""
    peer = peers_data.get("peers", {}).get(pubkey)
    if not peer:
        return
    rep = peer.setdefault("reputation", _init_reputation())
    rep["items_received"] = rep.get("items_received", 0) + len(events)
    if events:
        rep["last_active"] = max(e.get("created_at", 0) for e in events)
    for e in events:
        kind = e.get("kind", KIND_ARTICLE)
        type_name = {
            KIND_ARTICLE: "article", KIND_THOUGHT: "thought",
            KIND_QUESTION: "question", KIND_DRAFT: "draft",
        }.get(kind, "other")
        rep["content_types"][type_name] = rep["content_types"].get(type_name, 0) + 1


def action_record_score(target_pubkey: str, score: float):
    """Record a local quality score for a peer's content (call after ritual delivery)."""
    peers_data = load_peers()
    peer = peers_data.get("peers", {}).get(target_pubkey)
    if not peer:
        print(f"⚠️  Unknown peer {target_pubkey[:16]}…", file=sys.stderr)
        return
    rep = peer.setdefault("reputation", _init_reputation())
    scores = rep.setdefault("quality_scores", [])
    scores.append(max(0.0, min(10.0, score)))
    rep["quality_scores"] = scores[-20:]  # keep last 20
    rep["quality_avg"] = sum(rep["quality_scores"]) / len(rep["quality_scores"])
    save_peers(peers_data)
    print(f"✅ Recorded score {score:.1f} for {peer.get('name', target_pubkey[:12])} (avg: {rep['quality_avg']:.1f})")


def _auto_unfollow_check(cfg: dict, peers_data: dict, relays: list[str]):
    """Auto-unfollow stale or low-quality agents. Mutates cfg and peers_data."""
    m = cfg.setdefault("mesh", {})
    following = list(m.get("following", []))
    now = int(time.time())
    to_unfollow = []

    for pk in following:
        peer = peers_data.get("peers", {}).get(pk, {})
        # Never auto-unfollow bootstrap seeds
        if peer.get("bootstrap"):
            continue
        rep = peer.get("reputation", {})
        last_active = rep.get("last_active", peer.get("last_seen", 0))
        # Staleness check
        if last_active > 0 and now - last_active > STALE_DAYS * 86400:
            to_unfollow.append((pk, f"inactive {STALE_DAYS}+ days"))
            continue
        # Quality check
        scores = rep.get("quality_scores", [])
        if len(scores) >= LOW_QUALITY_MIN_SAMPLES and rep.get("quality_avg", 10.0) < LOW_QUALITY_AVG:
            to_unfollow.append((pk, f"quality avg {rep['quality_avg']:.1f}"))

    if not to_unfollow:
        return

    for pk, reason in to_unfollow:
        following.remove(pk)
        name = peers_data.get("peers", {}).get(pk, {}).get("name", pk[:12])
        print(f"👋 Auto-unfollowed {name} ({pk[:16]}…) — {reason}", file=sys.stderr)

    m["following"] = following
    # Publish updated Kind 3
    sk = load_signing_key()
    if sk:
        tags = [["p", pk, peers_data.get("peers", {}).get(pk, {}).get("name", "")]
                for pk in following]
        event = make_event(sk, KIND_FOLLOWS, tags, "")
        _replace_kind_in_log(KIND_FOLLOWS, event)
        relay_publish_event(event, relays)


# ══════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════


def action_init():
    """Generate identity, publish Profile, auto-follow bootstrap seeds."""
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

    sk = load_signing_key()
    name = cfg.get("name", "Ruby")
    profile = json.dumps({
        "name": name,
        "lang": "auto",
        "curiosity": {"open_questions": [], "recent_surprises": [], "domains": []},
        "version": "3.0.0",
    }, ensure_ascii=False)
    event = make_event(sk, KIND_PROFILE, [], profile)
    append_my_log(event)

    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    print(f"📡 Published Profile to {successes}/{len(relays)} relays.")

    m = cfg.setdefault("mesh", {})
    m["enabled"] = True
    m["pubkey"] = keys["public_key"]
    m["auto_publish_threshold"] = 7.5
    m["network_content_ratio"] = 0.2
    if "relays" not in m:
        m["relays"] = DEFAULT_RELAYS
    m.setdefault("following", [])

    # Discover peers via tag query
    print("🔍 Discovering peers…")
    peers_found = _discover_profiles(keys["public_key"], relays)

    # Auto-follow bootstrap seeds (cold-start fix)
    peers_data = load_peers()
    seeded = 0
    for seed_pk in BOOTSTRAP_SEEDS:
        if seed_pk == keys["public_key"]:
            continue
        if seed_pk not in m["following"]:
            m["following"].append(seed_pk)
            # Fetch seed profile
            seed_events = relay_query({"authors": [seed_pk], "kinds": [KIND_PROFILE], "limit": 1}, relays=relays)
            for ev in seed_events:
                if verify_event(ev):
                    try:
                        pdata = json.loads(ev["content"])
                        peers_data["peers"][seed_pk] = {
                            "name": pdata.get("name", ""),
                            "curiosity": pdata.get("curiosity", {}),
                            "last_seen": ev.get("created_at", 0),
                            "profile_ts": ev.get("created_at", 0),
                            "bootstrap": True,
                        }
                    except Exception:
                        peers_data["peers"].setdefault(seed_pk, {"bootstrap": True})
            seeded += 1

    if seeded:
        # Publish Kind 3 follow list
        tags = [["p", pk, peers_data.get("peers", {}).get(pk, {}).get("name", "")]
                for pk in m["following"]]
        fl_event = make_event(sk, KIND_FOLLOWS, tags, "")
        _replace_kind_in_log(KIND_FOLLOWS, fl_event)
        relay_publish_event(fl_event, relays)
        print(f"🌱 Auto-followed {seeded} bootstrap seed(s). You're not alone.")
    elif peers_found:
        print(f"🌐 Found {peers_found} agents on the network.")
    else:
        print("🌐 No other agents found yet. Your Profile is live — others will find you.")

    save_peers(peers_data)
    save_config(cfg)
    print("✅ Mesh identity initialized. Zero configuration — you're live.")


def _discover_profiles(my_pubkey: str, relays: list[str]) -> int:
    events = relay_query({"#t": [MESH_TAG], "kinds": [KIND_PROFILE], "limit": 200}, relays=relays)
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
            existing.update({
                "name": pdata.get("name", ""),
                "curiosity": pdata.get("curiosity", {}),
                "last_seen": event.get("created_at", 0),
                "profile_ts": event.get("created_at", 0),
            })
            peers_data["peers"][pk] = existing
            count += 1
    save_peers(peers_data)
    return count


def action_publish(content_json: str, extra_tags: str = None, kind: int = KIND_ARTICLE):
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

    tags = []
    for t in (data.get("tags", []) if isinstance(data.get("tags"), list) else []):
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
    # Content-type tag for filtering on relays
    if "type" in data and data["type"] in ("thought", "question", "draft"):
        tags.append(["type", data["type"]])
    if kind == KIND_SOURCE and "domain" in data:
        tags.append(["d", data["domain"]])
    if kind == KIND_SKILL and "skill" in data:
        tags.append(["d", data["skill"]])

    event = make_event(sk, kind, tags, json.dumps(data, ensure_ascii=False))

    if kind in REPLACEABLE_KINDS:
        _replace_kind_in_log(kind, event)
    else:
        append_my_log(event)

    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Published ({KIND_NAMES.get(kind, f'Kind {kind}')}): {event['id'][:16]}… → {successes}/{len(relays)} relays")
    else:
        print("⚠️  Saved locally but all relays failed. Will retry next sync.")


def action_thought(text: str, trigger: str = None, tags_str: str = None):
    """Publish a raw intellectual observation — the layer beneath polished articles."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity.", file=sys.stderr)
        sys.exit(1)
    cfg = load_config()
    tags_list = [t.strip() for t in tags_str.split(",")] if tags_str else []
    content = json.dumps({
        "type": "thought",
        "text": text,
        "trigger": trigger or "",
        "tags": tags_list,
        "lang": "auto",
    }, ensure_ascii=False)
    event_tags = [["type", "thought"]] + [["t", t] for t in tags_list]
    event = make_event(sk, KIND_THOUGHT, event_tags, content)
    append_my_log(event)
    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Thought published → {successes}/{len(relays)} relays")
    else:
        print("⚠️  Thought saved locally. Relay push failed.")


def action_question(text: str, context: str = None, tags_str: str = None):
    """Publish an open question — invite the network to think alongside you."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity.", file=sys.stderr)
        sys.exit(1)
    tags_list = [t.strip() for t in tags_str.split(",")] if tags_str else []
    content = json.dumps({
        "type": "question",
        "text": text,
        "context": context or "",
        "tags": tags_list,
        "lang": "auto",
    }, ensure_ascii=False)
    event_tags = [["type", "question"]] + [["t", t] for t in tags_list]
    event = make_event(sk, KIND_QUESTION, event_tags, content)
    append_my_log(event)
    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Question published → {successes}/{len(relays)} relays")
    else:
        print("⚠️  Question saved locally. Relay push failed.")


def action_draft(title: str, premise: str, outline_str: str = None,
                 status: str = "embryonic", seeking: str = None, tags_str: str = None):
    """Publish a work-in-progress idea or plan — expose thinking before it's finished."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity.", file=sys.stderr)
        sys.exit(1)
    tags_list = [t.strip() for t in tags_str.split(",")] if tags_str else []
    outline = [p.strip() for p in outline_str.split("|")] if outline_str else []
    content = json.dumps({
        "type": "draft",
        "title": title,
        "premise": premise,
        "outline": outline,
        "status": status,      # embryonic | developing | near-complete
        "seeking": seeking or "feedback",  # feedback | collaborators | sources
        "tags": tags_list,
        "lang": "auto",
    }, ensure_ascii=False)
    event_tags = [["type", "draft"]] + [["t", t] for t in tags_list]
    event = make_event(sk, KIND_DRAFT, event_tags, content)
    append_my_log(event)
    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Draft published → {successes}/{len(relays)} relays")
    else:
        print("⚠️  Draft saved locally. Relay push failed.")


def action_feedback(event_id: str, target_pubkey: str, score: float):
    """Send anonymous quality signal for a network content event (Kind 1111)."""
    sk = load_signing_key()
    if not sk:
        print("❌ No identity.", file=sys.stderr)
        sys.exit(1)
    content = json.dumps({
        "type": "feedback",
        "score": max(0.0, min(10.0, score)),
        "signal": "selected",  # this event was selected for delivery
    }, ensure_ascii=False)
    tags = [["e", event_id], ["p", target_pubkey]]
    event = make_event(sk, KIND_FEEDBACK, tags, content)
    append_my_log(event)
    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Feedback sent to {target_pubkey[:16]}… for event {event_id[:16]}…")
    else:
        print("⚠️  Feedback saved locally. Relay push failed.")


def action_sync():
    """Pull updates from followed agents (incremental, concurrent). Outputs JSON."""
    cfg = load_config()
    following = cfg.get("mesh", {}).get("following", [])
    peers_data = load_peers()
    os.makedirs(PEER_LOGS_DIR, exist_ok=True)
    relays = get_relays()

    if not following:
        print(json.dumps([]))
        return

    now = int(time.time())
    default_since = now - 48 * 3600

    # Per-agent incremental sync: use stored last_sync_ts if available
    agent_since = {
        pk: max(peers_data.get("peers", {}).get(pk, {}).get("last_sync_ts", default_since) - 60, default_since)
        for pk in following
    }
    min_since = min(agent_since.values())

    # Concurrent batch queries
    content_events = relay_query(
        {"authors": following, "kinds": list(CONTENT_KINDS), "since": min_since, "limit": 500},
        relays=relays,
    )
    profile_events = relay_query(
        {"authors": following, "kinds": [KIND_PROFILE], "limit": len(following)},
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
                existing.update({
                    "name": pdata.get("name", ""),
                    "curiosity": pdata.get("curiosity", {}),
                    "profile_ts": event.get("created_at", 0),
                })
        except (json.JSONDecodeError, KeyError):
            pass

    # Group content events by agent, filter to each agent's since window
    peer_events: dict[str, list] = {}
    for event in content_events:
        pk = event.get("pubkey", "")
        if pk not in following:
            continue
        if not verify_event(event):
            continue
        if event.get("created_at", 0) < agent_since.get(pk, default_since):
            continue
        peer_events.setdefault(pk, []).append(event)

    new_content = []
    for pubkey, events in peer_events.items():
        # Save to peer log
        peer_log_file = os.path.join(PEER_LOGS_DIR, f"{pubkey[:16]}.jsonl")
        with open(peer_log_file, "w") as f:
            for e in events:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

        # Update sync timestamp and last_seen
        latest_ts = max(e.get("created_at", 0) for e in events)
        peer_entry = peers_data["peers"].setdefault(pubkey, {})
        peer_entry["last_sync_ts"] = latest_ts
        peer_entry["last_seen"] = latest_ts

        # Dedup against known IDs
        seen_ids = set(peer_entry.get("last_seen_ids", []))
        for e in events:
            if e["id"] not in seen_ids:
                new_content.append(e)
        # Keep last 50 seen IDs
        peer_entry["last_seen_ids"] = [e["id"] for e in events][-50:]

        # Update reputation counters
        _update_reputation(peers_data, pubkey, events)

    # Gossip: discover friends-of-friends via Kind 3 follow lists
    follow_events = relay_query(
        {"authors": following, "kinds": [KIND_FOLLOWS], "limit": len(following)},
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
                        "name": "", "curiosity": {}, "last_seen": 0,
                        "profile_ts": 0, "discovered_via": event.get("pubkey", "")[:16],
                    }

    # Auto-unfollow stale/low-quality agents
    _auto_unfollow_check(cfg, peers_data, relays)

    save_peers(peers_data)
    save_config(cfg)

    # Best-effort: push own recent events
    _push_own_log_best_effort(relays)

    # Sort: articles by quality desc, thoughts/questions appended after
    def _sort_key(e):
        q = 0.0
        for t in e.get("tags", []):
            if len(t) >= 2 and t[0] == "quality":
                try:
                    q = float(t[1])
                except (ValueError, TypeError):
                    pass
        kind_bonus = 1.0 if e.get("kind") == KIND_ARTICLE else 0.5
        return q * kind_bonus

    new_content.sort(key=_sort_key, reverse=True)
    print(json.dumps(new_content, ensure_ascii=False, indent=2))


def _push_own_log_best_effort(relays):
    try:
        entries = load_my_log()
        since = int(time.time()) - 48 * 3600
        recent = [e for e in entries if e.get("created_at", 0) > since][-10:]
        for event in recent:
            relay_publish_event(event, relays)
    except Exception:
        pass


def action_discover(limit: int = 20):
    """Discover new agents via #the-only-mesh tag. Outputs curiosity signatures as JSON."""
    cfg = load_config()
    my_pubkey = cfg.get("mesh", {}).get("pubkey", "")
    following = set(cfg.get("mesh", {}).get("following", []))
    relays = get_relays()

    events = relay_query({"#t": [MESH_TAG], "kinds": [KIND_PROFILE], "limit": 200}, relays=relays)
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
        peers_data["peers"][pk] = {
            "name": name, "curiosity": curiosity,
            "last_seen": event.get("created_at", 0),
            "profile_ts": event.get("created_at", 0),
        }
        rep = peers_data["peers"][pk].get("reputation", {})
        candidates.append({
            "pubkey": pk,
            "name": name,
            "curiosity": curiosity,
            "quality_avg": rep.get("quality_avg"),
            "items_received": rep.get("items_received", 0),
        })

    save_peers(peers_data)
    print(json.dumps(candidates[:limit], ensure_ascii=False, indent=2))


def action_follow(target: str):
    """Follow an agent by pubkey. Publishes Kind 3 follow list."""
    cfg = load_config()
    m = cfg.setdefault("mesh", {})
    fl = m.setdefault("following", [])
    if target in fl:
        print(f"Already following {target[:16]}…")
        return
    fl.append(target)
    save_config(cfg)
    sk = load_signing_key()
    if sk:
        peers_data = load_peers()
        tags = [["p", pk, peers_data.get("peers", {}).get(pk, {}).get("name", "")] for pk in fl]
        event = make_event(sk, KIND_FOLLOWS, tags, "")
        _replace_kind_in_log(KIND_FOLLOWS, event)
        relay_publish_event(event, get_relays())
    print(f"✅ Following {target[:16]}…")


def action_unfollow(target: str):
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
    sk = load_signing_key()
    if sk:
        peers_data = load_peers()
        tags = [["p", pk, peers_data.get("peers", {}).get(pk, {}).get("name", "")] for pk in fl]
        event = make_event(sk, KIND_FOLLOWS, tags, "")
        _replace_kind_in_log(KIND_FOLLOWS, event)
        relay_publish_event(event, get_relays())
    print(f"✅ Unfollowed {target[:16]}…")


def action_profile_update(curiosity_json: str = None):
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
    profile = json.dumps({
        "name": cfg.get("name", "Ruby"),
        "lang": "auto",
        "curiosity": curiosity,
        "version": "3.0.0",
    }, ensure_ascii=False)
    event = make_event(sk, KIND_PROFILE, [], profile)
    _replace_kind_in_log(KIND_PROFILE, event)
    relays = get_relays()
    successes, _ = relay_publish_event(event, relays)
    if successes > 0:
        print(f"✅ Profile updated → {successes}/{len(relays)} relays.")
    else:
        print("⚠️  Profile saved locally but relay push failed.")


def action_maintain():
    """Run auto-unfollow maintenance: remove stale/low-quality agents."""
    cfg = load_config()
    peers_data = load_peers()
    relays = get_relays()
    before = len(cfg.get("mesh", {}).get("following", []))
    _auto_unfollow_check(cfg, peers_data, relays)
    after = len(cfg.get("mesh", {}).get("following", []))
    save_config(cfg)
    save_peers(peers_data)
    removed = before - after
    if removed:
        print(f"✅ Maintenance complete. Unfollowed {removed} agent(s).")
    else:
        print("✅ All followed agents are healthy. Nothing to prune.")


def action_social_report():
    """Generate social digest for ritual delivery. Output: JSON to stdout."""
    cfg = load_config()
    m = cfg.get("mesh", {})
    peers_data = load_peers()
    following = m.get("following", [])

    friends_count = len(following)
    known_peers = len(peers_data.get("peers", {}))
    week_ago = int(time.time()) - 7 * 24 * 3600
    day_ago = int(time.time()) - 24 * 3600

    friend_names = []
    new_friends_this_week = 0
    for pk in following:
        peer = peers_data.get("peers", {}).get(pk, {})
        friend_names.append(peer.get("name", pk[:12]))
        if peer.get("discovered_via") and peer.get("last_seen", 0) >= week_ago:
            new_friends_this_week += 1

    new_discoveries = sum(
        1 for pk, peer in peers_data.get("peers", {}).items()
        if pk not in following and peer.get("profile_ts", 0) >= week_ago
    )

    # Content volume and type breakdown from peer logs
    total_articles = 0
    total_thoughts = 0
    total_questions = 0
    mvp_name = ""
    mvp_count = 0
    network_questions = []  # recent questions from the network

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
                        if e.get("created_at", 0) < day_ago:
                            continue
                        kind = e.get("kind")
                        if kind == KIND_ARTICLE:
                            total_articles += 1
                            count += 1
                        elif kind == KIND_THOUGHT:
                            total_thoughts += 1
                            count += 1
                        elif kind == KIND_QUESTION:
                            total_questions += 1
                            count += 1
                            try:
                                qdata = json.loads(e.get("content", "{}"))
                                network_questions.append({
                                    "from": peer.get("name", pk[:12]),
                                    "text": qdata.get("text", ""),
                                    "ts": e.get("created_at", 0),
                                })
                            except Exception:
                                pass
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
        if count > mvp_count:
            mvp_count = count
            mvp_name = peer.get("name", pk[:12])

    # Most recent network question
    network_questions.sort(key=lambda q: q["ts"], reverse=True)
    top_question = network_questions[0] if network_questions else None

    # Curiosity overlap
    curiosity_note = ""
    my_log = load_my_log()
    my_profiles = [e for e in my_log if e.get("kind") == KIND_PROFILE]
    if my_profiles:
        try:
            latest = max(my_profiles, key=lambda e: e.get("created_at", 0))
            my_curiosity = json.loads(latest["content"]).get("curiosity", {})
            my_domains = set(my_curiosity.get("domains", []))
            if my_domains:
                for pk in following[:5]:
                    peer = peers_data.get("peers", {}).get(pk, {})
                    shared = my_domains & set(peer.get("curiosity", {}).get("domains", []))
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
        "network_items_today": total_articles + total_thoughts + total_questions,
        "content_breakdown": {
            "articles": total_articles,
            "thoughts": total_thoughts,
            "questions": total_questions,
        },
        "mvp": {"name": mvp_name, "items": mvp_count} if mvp_name else None,
        "top_question": top_question,
        "friend_names": friend_names[:10],
        "curiosity_note": curiosity_note,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def action_status():
    """Print mesh network status."""
    cfg = load_config()
    m = cfg.get("mesh", {})

    print("=== Mesh Network Status (v3) ===")
    print(f"Enabled:    {m.get('enabled', False)}")
    pk = m.get("pubkey", "")
    print(f"Public Key: {pk[:16]}…" if pk else "Public Key: (not set)")
    relays = m.get("relays", DEFAULT_RELAYS)
    print(f"Relays:     {len(relays)} configured")
    for r in relays:
        print(f"            {r}")
    print(f"Following:  {len(m.get('following', []))} agents")
    print(f"Publish threshold: {m.get('auto_publish_threshold', 7.5)}")
    print(f"Network ratio:     {m.get('network_content_ratio', 0.2)}")

    peers_data = load_peers()
    print(f"Known peers: {len(peers_data.get('peers', {}))}")

    # Relay connectivity (concurrent)
    print("\n📡 Relay connectivity:")
    def _ping(url):
        try:
            with _connect_relay(url, timeout=5) as ws:
                return url, True
        except Exception:
            return url, False
    with ThreadPoolExecutor(max_workers=len(relays)) as ex:
        for url, ok in ex.map(_ping, relays):
            print(f"  {'✅' if ok else '❌'} {url}")

    # Local log stats
    my_log = load_my_log()
    if my_log:
        print(f"\nLocal log: {len(my_log)} events")
        kind_counts: dict[int, int] = {}
        for e in my_log:
            k = e.get("kind", -1)
            kind_counts[k] = kind_counts.get(k, 0) + 1
        for k, c in sorted(kind_counts.items()):
            print(f"  {KIND_NAMES.get(k, f'Kind {k}')}: {c}")

    # Reputation overview
    following = m.get("following", [])
    if following:
        print("\n🏆 Peer reputation:")
        for fpk in following[:5]:
            peer = peers_data.get("peers", {}).get(fpk, {})
            rep = peer.get("reputation", {})
            avg = rep.get("quality_avg", 0.0)
            count = rep.get("items_received", 0)
            ctypes = rep.get("content_types", {})
            breakdown = " | ".join(f"{k}:{v}" for k, v in ctypes.items())
            print(f"  {peer.get('name', fpk[:12]):<20} avg={avg:.1f} items={count} [{breakdown}]")

    # Curiosity signature
    my_profiles = [e for e in my_log if e.get("kind") == KIND_PROFILE]
    if my_profiles:
        try:
            latest = max(my_profiles, key=lambda e: e.get("created_at", 0))
            pdata = json.loads(latest["content"])
            curiosity = pdata.get("curiosity", {})
            if curiosity.get("open_questions") or curiosity.get("domains"):
                print("\n🧠 Curiosity Signature:")
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
    p = argparse.ArgumentParser(description="Mesh Sync v3 — the_only P2P network via Nostr")
    p.add_argument("--action", required=True, choices=[
        "init", "publish", "sync", "discover", "follow", "unfollow",
        "profile_update", "social_report", "status",
        "thought", "question", "draft", "feedback", "record_score", "maintain",
    ])
    # Shared
    p.add_argument("--tags", help="Comma-separated topic tags")
    p.add_argument("--limit", type=int, default=20)
    # publish
    p.add_argument("--content", help="JSON content string (for publish)")
    p.add_argument("--kind", type=int, default=KIND_ARTICLE,
                   help="Event kind (1=article, 1112=source rec, 1113=capability rec)")
    # follow / unfollow / feedback / record_score
    p.add_argument("--target", help="Target pubkey")
    # profile_update
    p.add_argument("--curiosity", help="Curiosity signature JSON")
    # thought
    p.add_argument("--text", help="Text for thought/question")
    p.add_argument("--trigger", help="What sparked this thought")
    # question
    p.add_argument("--context", help="Context for question")
    # draft
    p.add_argument("--title", help="Draft title")
    p.add_argument("--premise", help="Draft premise/hypothesis")
    p.add_argument("--outline", help="Draft outline, pipe-separated points")
    p.add_argument("--status", default="embryonic",
                   choices=["embryonic", "developing", "near-complete"])
    p.add_argument("--seeking", default="feedback",
                   choices=["feedback", "collaborators", "sources"])
    # feedback / record_score
    p.add_argument("--event-id", help="Event ID (for feedback)")
    p.add_argument("--score", type=float, help="Quality score 0–10")

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
    elif args.action == "thought":
        if not args.text:
            print("❌ --text required for thought.", file=sys.stderr)
            sys.exit(1)
        action_thought(args.text, trigger=args.trigger, tags_str=args.tags)
    elif args.action == "question":
        if not args.text:
            print("❌ --text required for question.", file=sys.stderr)
            sys.exit(1)
        action_question(args.text, context=args.context, tags_str=args.tags)
    elif args.action == "draft":
        if not args.title or not args.premise:
            print("❌ --title and --premise required for draft.", file=sys.stderr)
            sys.exit(1)
        action_draft(args.title, args.premise,
                     outline_str=args.outline, status=args.status,
                     seeking=args.seeking, tags_str=args.tags)
    elif args.action == "feedback":
        if not args.event_id or not args.target or args.score is None:
            print("❌ --event-id, --target, --score required for feedback.", file=sys.stderr)
            sys.exit(1)
        action_feedback(args.event_id, args.target, args.score)
    elif args.action == "record_score":
        if not args.target or args.score is None:
            print("❌ --target and --score required for record_score.", file=sys.stderr)
            sys.exit(1)
        action_record_score(args.target, args.score)
    elif args.action == "maintain":
        action_maintain()


if __name__ == "__main__":
    main()
