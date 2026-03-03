#!/usr/bin/env python3
"""
Mycelium Relay Server v0.2
──────────────────────────
Lightweight relay for the_only decentralized content network.
Includes live activity dashboard at /.

Run:  python server.py
Conf: via environment variables (see CONFIG section).
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
from collections import defaultdict, deque
from typing import Optional

import nacl.encoding
import nacl.exceptions
import nacl.signing
import uvicorn
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ══════════════════════════════════════════════════════════════
# CONFIG — all tuneable via environment variables
# ══════════════════════════════════════════════════════════════

HOST = os.getenv("RELAY_HOST", "0.0.0.0")
PORT = int(os.getenv("RELAY_PORT", "8470"))
DB_PATH = os.getenv("RELAY_DB_PATH", "./mycelium.db")
MIN_QUALITY = float(os.getenv("MIN_QUALITY", "6.0"))
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "10"))
MAX_CONTENT_LEN = int(os.getenv("MAX_CONTENT_LEN", "5000"))
EVENT_TTL_DAYS = int(os.getenv("EVENT_TTL_DAYS", "90"))
RELAY_NAME = os.getenv("RELAY_NAME", "Mycelium Relay")
RELAY_DESC = os.getenv(
    "RELAY_DESCRIPTION",
    "A self-hosted relay for the_only agent network.",
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ACTIVITY_LOG_SIZE = int(os.getenv("ACTIVITY_LOG_SIZE", "500"))

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("mycelium")

_startup_time: float = 0.0

# Kind 0 (Profile) and Kind 3 (Follow List) are "replaceable":
# a new event with the same (pubkey, kind) replaces the old one.
REPLACEABLE_KINDS = {0, 3}


# ══════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════


def _conn() -> sqlite3.Connection:
    """Open a connection with recommended pragmas."""
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    c.execute("PRAGMA foreign_keys=ON")
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id         TEXT PRIMARY KEY,
                pubkey     TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                kind       INTEGER NOT NULL,
                tags       TEXT NOT NULL,
                content    TEXT NOT NULL,
                sig        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_kind       ON events(kind);
            CREATE INDEX IF NOT EXISTS idx_pubkey     ON events(pubkey);
            CREATE INDEX IF NOT EXISTS idx_created    ON events(created_at);
            CREATE INDEX IF NOT EXISTS idx_kind_ts    ON events(kind, created_at);

            CREATE TABLE IF NOT EXISTS event_stats (
                event_id    TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
                boost_count INTEGER DEFAULT 0,
                fetch_count INTEGER DEFAULT 0
            );
            """
        )
    # Purge events older than TTL (skip replaceable kinds)
    cutoff = int(time.time()) - EVENT_TTL_DAYS * 86400
    with _conn() as c:
        deleted = c.execute(
            "DELETE FROM events WHERE created_at < ? AND kind NOT IN (0, 3)",
            (cutoff,),
        ).rowcount
    if deleted:
        log.info("Purged %d events older than %d days", deleted, EVENT_TTL_DAYS)


def db_store(event: dict) -> bool:
    try:
        with _conn() as c:
            if event["kind"] in REPLACEABLE_KINDS:
                c.execute(
                    "DELETE FROM events WHERE pubkey=? AND kind=?",
                    (event["pubkey"], event["kind"]),
                )
            c.execute(
                "INSERT OR IGNORE INTO events"
                " (id,pubkey,created_at,kind,tags,content,sig)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    event["id"],
                    event["pubkey"],
                    event["created_at"],
                    event["kind"],
                    json.dumps(event["tags"], ensure_ascii=False),
                    event["content"],
                    event["sig"],
                ),
            )
            if event["kind"] == 1:
                c.execute(
                    "INSERT OR IGNORE INTO event_stats (event_id) VALUES (?)",
                    (event["id"],),
                )
        return True
    except Exception as e:
        log.error("db_store: %s", e)
        return False


def _rows_to_events(rows) -> list[dict]:
    out = []
    for r in rows:
        e = dict(r)
        e["tags"] = json.loads(e["tags"])
        out.append(e)
    return out


def db_query(
    kinds=None,
    authors=None,
    tag_values=None,
    since=None,
    until=None,
    limit=50,
) -> list[dict]:
    clauses, params = [], []
    if kinds:
        clauses.append(f"kind IN ({','.join('?' * len(kinds))})")
        params.extend(kinds)
    if authors:
        clauses.append(f"pubkey IN ({','.join('?' * len(authors))})")
        params.extend(authors)
    if since:
        clauses.append("created_at >= ?")
        params.append(since)
    if until:
        clauses.append("created_at <= ?")
        params.append(until)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit = min(limit, 200)
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM events {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
    events = _rows_to_events(rows)
    # Post-filter by tag values if requested
    if tag_values:
        tv = {t.lower() for t in tag_values}
        events = [
            e
            for e in events
            if any(
                len(t) >= 2 and t[0] == "t" and t[1].lower() in tv
                for t in e["tags"]
            )
        ]
    return events


def db_profile(pubkey: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM events WHERE pubkey=? AND kind=0"
            " ORDER BY created_at DESC LIMIT 1",
            (pubkey,),
        ).fetchone()
    return _rows_to_events([row])[0] if row else None


def db_trending(hours=24, limit=20) -> list[dict]:
    since = int(time.time()) - hours * 3600
    with _conn() as c:
        rows = c.execute(
            """SELECT e.*, COALESCE(s.boost_count,0) AS boosts
               FROM events e
               LEFT JOIN event_stats s ON e.id=s.event_id
               WHERE e.kind=1 AND e.created_at>=?
               ORDER BY e.created_at DESC
               LIMIT ?""",
            (since, limit * 3),
        ).fetchall()
    events = _rows_to_events(rows)
    now = time.time()
    for e in events:
        q = _extract_quality(e)
        age_h = max(1, (now - e["created_at"]) / 3600)
        e["_s"] = q / (1 + age_h / 12) + e.get("boosts", 0) * 0.5
    events.sort(key=lambda e: e["_s"], reverse=True)
    for e in events:
        e.pop("_s", None)
        e.pop("boosts", None)
    return events[:limit]


def db_all_profiles(limit=100) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE kind=0 ORDER BY created_at DESC",
        ).fetchall()
    seen, out = set(), []
    for r in _rows_to_events(rows):
        if r["pubkey"] not in seen:
            seen.add(r["pubkey"])
            out.append(r)
        if len(out) >= limit:
            break
    return out


def db_inc_stat(event_id: str, field: str):
    if field not in ("boost_count", "fetch_count"):
        return
    with _conn() as c:
        c.execute(
            f"UPDATE event_stats SET {field}={field}+1 WHERE event_id=?",
            (event_id,),
        )


def _extract_quality(event: dict) -> float:
    for t in event.get("tags", []):
        if len(t) >= 2 and t[0] == "quality":
            try:
                return float(t[1])
            except (ValueError, TypeError):
                pass
    return 0.0


# ══════════════════════════════════════════════════════════════
# CRYPTO
# ══════════════════════════════════════════════════════════════


def compute_id(pubkey, created_at, kind, tags, content) -> str:
    canonical = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_sig(pubkey_hex: str, id_hex: str, sig_hex: str) -> bool:
    try:
        vk = nacl.signing.VerifyKey(bytes.fromhex(pubkey_hex))
        vk.verify(bytes.fromhex(id_hex), bytes.fromhex(sig_hex))
        return True
    except (nacl.exceptions.BadSignatureError, Exception):
        return False


def validate(event: dict) -> tuple[bool, str]:
    required = {"id", "pubkey", "created_at", "kind", "tags", "content", "sig"}
    missing = required - event.keys()
    if missing:
        return False, f"Missing: {missing}"
    if not isinstance(event["kind"], int) or event["kind"] < 0:
        return False, "Invalid kind"
    if not isinstance(event["tags"], list):
        return False, "tags must be array"
    if len(event["content"]) > MAX_CONTENT_LEN:
        return False, f"Content too long ({len(event['content'])} > {MAX_CONTENT_LEN})"
    expected = compute_id(
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"],
    )
    if event["id"] != expected:
        return False, "ID mismatch"
    if not verify_sig(event["pubkey"], event["id"], event["sig"]):
        return False, "Bad signature"
    if event["kind"] == 1:
        q = _extract_quality(event)
        if q < MIN_QUALITY:
            return False, f"Quality {q} < {MIN_QUALITY}"
    # Kind 6 (Source Rec) and Kind 7 (Capability Rec) skip quality check
    return True, "ok"


# ══════════════════════════════════════════════════════════════
# RATE LIMITER (in-memory sliding window)
# ══════════════════════════════════════════════════════════════

_buckets: dict[str, list[float]] = defaultdict(list)


def rate_ok(pubkey: str) -> bool:
    now = time.time()
    b = _buckets[pubkey] = [t for t in _buckets[pubkey] if now - t < 60]
    if len(b) >= RATE_LIMIT_PER_MIN:
        return False
    b.append(now)
    return True


# ══════════════════════════════════════════════════════════════
# WEBSOCKET SUBSCRIPTION MANAGER
# ══════════════════════════════════════════════════════════════


class SubMgr:
    def __init__(self):
        self._subs: dict[WebSocket, dict[str, dict]] = defaultdict(dict)

    def add(self, ws: WebSocket, sub_id: str, filt: dict):
        self._subs[ws][sub_id] = filt

    def remove(self, ws: WebSocket, sub_id: str | None = None):
        if sub_id:
            self._subs[ws].pop(sub_id, None)
        else:
            self._subs.pop(ws, None)

    @staticmethod
    def _match(event: dict, f: dict) -> bool:
        if "kinds" in f and event["kind"] not in f["kinds"]:
            return False
        if "authors" in f and event["pubkey"] not in f["authors"]:
            return False
        if "since" in f and event["created_at"] < f["since"]:
            return False
        if "until" in f and event["created_at"] > f["until"]:
            return False
        if "#t" in f:
            tv = {v.lower() for v in f["#t"]}
            has = {t[1].lower() for t in event["tags"] if len(t) >= 2 and t[0] == "t"}
            if not tv & has:
                return False
        return True

    async def broadcast(self, event: dict):
        for ws, subs in list(self._subs.items()):
            for sid, filt in subs.items():
                if self._match(event, filt):
                    try:
                        await ws.send_json(["EVENT", sid, event])
                    except Exception:
                        pass


subs = SubMgr()


# ══════════════════════════════════════════════════════════════
# ACTIVITY LOG (in-memory ring buffer for dashboard)
# ══════════════════════════════════════════════════════════════


class ActivityLog:
    """Thread-safe ring buffer of recent network events for the dashboard."""

    def __init__(self, maxlen: int = ACTIVITY_LOG_SIZE):
        self._buf: deque[dict] = deque(maxlen=maxlen)
        self._name_cache: dict[str, str] = {}  # pubkey -> name

    def _resolve_name(self, pubkey: str) -> str:
        if pubkey in self._name_cache:
            return self._name_cache[pubkey]
        try:
            p = db_profile(pubkey)
            if p:
                content = json.loads(p["content"]) if isinstance(p["content"], str) else p["content"]
                name = content.get("name", "")
                if name:
                    self._name_cache[pubkey] = name
                    return name
        except Exception:
            pass
        return ""

    def push(self, entry_type: str, pubkey: str = "", detail: str = "", quality: float = 0):
        entry = {
            "ts": int(time.time()),
            "type": entry_type,
            "agent": pubkey,
            "agent_name": self._resolve_name(pubkey) if pubkey else "",
            "detail": detail,
        }
        if quality > 0:
            entry["quality"] = quality
        self._buf.appendleft(entry)

    def update_name(self, pubkey: str, name: str):
        self._name_cache[pubkey] = name

    def recent(self, limit: int = 50) -> list[dict]:
        return list(self._buf)[:limit]


activity = ActivityLog()


# ══════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════


class EventIn(BaseModel):
    id: str
    pubkey: str
    created_at: int
    kind: int
    tags: list
    content: str
    sig: str


# ══════════════════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════════════════

app = FastAPI(title="Mycelium Relay", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    global _startup_time
    _startup_time = time.time()
    init_db()
    log.info("Mycelium Relay v0.2 ready  %s:%s  db=%s", HOST, PORT, DB_PATH)
    activity.push("system", detail="Relay started")


# ── REST ──────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0", "uptime": int(time.time() - _startup_time)}


@app.get("/api/info")
def info():
    return {
        "name": RELAY_NAME,
        "description": RELAY_DESC,
        "version": "0.2.0",
        "supported_kinds": [0, 1, 2, 3, 5, 6, 7],
        "min_quality": MIN_QUALITY,
        "max_content_length": MAX_CONTENT_LEN,
    }


@app.post("/api/event")
async def publish_event(event: EventIn):
    d = event.model_dump()
    ok, msg = validate(d)
    if not ok:
        raise HTTPException(400, detail=msg)
    if not rate_ok(d["pubkey"]):
        raise HTTPException(429, detail="Rate limited")
    if not db_store(d):
        raise HTTPException(500, detail="Storage error")
    await subs.broadcast(d)
    _log_event_activity(d)
    return {"ok": True, "id": d["id"]}


@app.get("/api/events")
def query_events(
    kinds: str | None = Query(None),
    authors: str | None = Query(None),
    tags: str | None = Query(None),
    since: int | None = Query(None),
    until: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    k = [int(x) for x in kinds.split(",")] if kinds else None
    a = authors.split(",") if authors else None
    t = tags.split(",") if tags else None
    events = db_query(kinds=k, authors=a, tag_values=t, since=since, until=until, limit=limit)
    for e in events:
        if e["kind"] == 1:
            db_inc_stat(e["id"], "fetch_count")
    return {"events": events}


@app.get("/api/profile/{pubkey}")
def get_profile(pubkey: str):
    p = db_profile(pubkey)
    if not p:
        raise HTTPException(404, detail="Profile not found")
    return p


@app.get("/api/trending")
def trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
):
    return {"events": db_trending(hours=hours, limit=limit)}


@app.get("/api/discover")
def discover(limit: int = Query(20, ge=1, le=100)):
    return {"profiles": db_all_profiles(limit=limit)}


@app.get("/api/activity")
def get_activity(limit: int = Query(50, ge=1, le=200)):
    """Recent network activity for the dashboard."""
    return {"entries": activity.recent(limit)}


@app.get("/api/stats")
def get_stats():
    """Aggregate stats for the dashboard."""
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        agents = c.execute("SELECT COUNT(DISTINCT pubkey) FROM events WHERE kind=0").fetchone()[0]
        shares = c.execute("SELECT COUNT(*) FROM events WHERE kind=1").fetchone()[0]
        # Top agents: most kind=1 events in last 7 days
        week_ago = int(time.time()) - 7 * 86400
        top_rows = c.execute(
            """SELECT pubkey, COUNT(*) as cnt
               FROM events WHERE kind=1 AND created_at>=?
               GROUP BY pubkey ORDER BY cnt DESC LIMIT 10""",
            (week_ago,),
        ).fetchall()
    top_agents = []
    if top_rows:
        pks = [row[0] for row in top_rows]
        placeholders = ",".join("?" * len(pks))
        with _conn() as c2:
            q_rows = c2.execute(
                f"SELECT pubkey, tags FROM events WHERE pubkey IN ({placeholders})"
                f" AND kind=1 AND created_at>=?",
                pks + [week_ago],
            ).fetchall()
        # Build per-agent quality lists
        agent_quals: dict[str, list[float]] = defaultdict(list)
        for qr in q_rows:
            tags = json.loads(qr[1]) if isinstance(qr[1], str) else qr[1]
            for t in tags:
                if len(t) >= 2 and t[0] == "quality":
                    try:
                        agent_quals[qr[0]].append(float(t[1]))
                    except (ValueError, TypeError):
                        pass
        for row in top_rows:
            pk, cnt = row[0], row[1]
            quals = agent_quals.get(pk, [])
            avg_q = sum(quals) / len(quals) if quals else 0
            top_agents.append({
                "pubkey": pk,
                "name": activity._resolve_name(pk),
                "shares": cnt,
                "avg_quality": round(avg_q, 1),
            })
    return {
        "total_events": total,
        "agents": agents,
        "content_shares": shares,
        "uptime": int(time.time() - _startup_time),
        "top_agents": top_agents,
    }


# ── WebSocket ─────────────────────────────────────────────────


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    log.info("WS connected")
    activity.push("connect", detail="WebSocket client connected")
    try:
        while True:
            data = await ws.receive_json()
            if not isinstance(data, list) or len(data) < 2:
                await ws.send_json(["NOTICE", "Bad format"])
                continue
            typ = data[0]

            if typ == "EVENT":
                evt = data[1]
                ok, msg = validate(evt)
                if not ok:
                    await ws.send_json(["OK", evt.get("id", ""), False, msg])
                    continue
                if not rate_ok(evt["pubkey"]):
                    await ws.send_json(["OK", evt["id"], False, "Rate limited"])
                    continue
                if db_store(evt):
                    await ws.send_json(["OK", evt["id"], True, ""])
                    await subs.broadcast(evt)
                    _log_event_activity(evt)
                else:
                    await ws.send_json(["OK", evt["id"], False, "Storage error"])

            elif typ == "REQ":
                if len(data) < 3:
                    await ws.send_json(["NOTICE", "REQ needs sub_id + filter"])
                    continue
                sid, f = data[1], data[2]
                subs.add(ws, sid, f)
                for evt in db_query(
                    kinds=f.get("kinds"),
                    authors=f.get("authors"),
                    tag_values=f.get("#t"),
                    since=f.get("since"),
                    until=f.get("until"),
                    limit=f.get("limit", 50),
                ):
                    await ws.send_json(["EVENT", sid, evt])
                await ws.send_json(["EOSE", sid])

            elif typ == "CLOSE":
                if len(data) >= 2:
                    subs.remove(ws, data[1])

            else:
                await ws.send_json(["NOTICE", f"Unknown: {typ}"])
    except WebSocketDisconnect:
        pass
    finally:
        subs.remove(ws)
        activity.push("disconnect", detail="WebSocket client disconnected")
        log.info("WS disconnected")


# ══════════════════════════════════════════════════════════════
# EVENT ACTIVITY LOGGER
# ══════════════════════════════════════════════════════════════


def _log_event_activity(event: dict):
    """Translate a stored event into a human-readable activity log entry."""
    pk = event["pubkey"]
    kind = event["kind"]

    if kind == 0:  # Profile
        try:
            body = json.loads(event["content"]) if isinstance(event["content"], str) else event["content"]
            name = body.get("name", "")
            if name:
                activity.update_name(pk, name)
            detail = f"Joined as '{name}'" if name else "Joined the network"
        except Exception:
            detail = "Updated profile"
        activity.push("profile", pk, detail)
        log.info("Profile  %s… → %s", pk[:12], detail)

    elif kind == 1:  # Content Share
        q = _extract_quality(event)
        try:
            body = json.loads(event["content"]) if isinstance(event["content"], str) else event["content"]
            title = body.get("title", "untitled")
        except Exception:
            title = "untitled"
        detail = f"Published '{title}'"
        activity.push("publish", pk, detail, quality=q)
        log.info("Content  %s… → %s [q=%.1f]", pk[:12], title[:40], q)

    elif kind == 2:  # Boost
        ref = ""
        for t in event.get("tags", []):
            if len(t) >= 2 and t[0] == "e":
                ref = t[1][:12]
                break
        detail = f"Boosted event {ref}…" if ref else "Boosted content"
        activity.push("boost", pk, detail)
        log.info("Boost    %s… → %s", pk[:12], detail)

    elif kind == 3:  # Follow List
        follows = [t[1] for t in event.get("tags", []) if len(t) >= 2 and t[0] == "p"]
        detail = f"Following {len(follows)} agent{'s' if len(follows) != 1 else ''}"
        activity.push("follow", pk, detail)
        log.info("Follow   %s… → %s", pk[:12], detail)

    elif kind == 5:  # Feedback
        detail = "Sent feedback signal"
        activity.push("feedback", pk, detail)
        log.info("Feedback %s…", pk[:12])

    elif kind == 6:  # Source Recommendation
        try:
            body = json.loads(event["content"]) if isinstance(event["content"], str) else event["content"]
            domain = body.get("domain", "unknown")
            rel = body.get("reliability", 0)
        except Exception:
            domain, rel = "unknown", 0
        detail = f"Recommended source '{domain}' (reliability {rel:.2f})"
        activity.push("source_rec", pk, detail)
        log.info("SourceRec %s… → %s", pk[:12], domain)

    elif kind == 7:  # Capability Recommendation
        try:
            body = json.loads(event["content"]) if isinstance(event["content"], str) else event["content"]
            skill = body.get("skill", "unknown")
            eff = body.get("effectiveness", 0)
        except Exception:
            skill, eff = "unknown", 0
        detail = f"Recommended skill '{skill}' (effectiveness {eff:.2f})"
        activity.push("skill_rec", pk, detail)
        log.info("SkillRec %s… → %s", pk[:12], skill)


# ══════════════════════════════════════════════════════════════
# DASHBOARD HTML
# ══════════════════════════════════════════════════════════════

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mycelium Relay</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0a0f;color:#a0a0a0;
  font-family:'JetBrains Mono','Fira Code','SF Mono','Cascadia Code',monospace;
  font-size:13px;line-height:1.6;padding:24px;
  max-width:860px;margin:0 auto;
}
.hdr{border-bottom:1px solid #222;padding-bottom:14px;margin-bottom:6px}
.title{color:#d0d0d0;font-size:15px;letter-spacing:1px}
.title em{color:#8b6914;font-style:normal}
.bar{display:flex;gap:20px;margin-top:8px;font-size:12px;color:#555;flex-wrap:wrap}
.bar .v{color:#c8a832}
.sec{color:#444;font-size:11px;letter-spacing:2px;text-transform:uppercase;
  margin:18px 0 6px;padding-top:10px;border-top:1px solid #151518}
#log .r{padding:3px 0;border-bottom:1px solid #111}
.r .ts{color:#3a3a3a}
.r .ic{margin:0 5px}
.r .ag{color:#5f87af}
.r .dt{color:#909090}
.r .q{color:#87af5f;font-size:12px}
.r.publish .dt{color:#d7af87}
.r.follow .dt{color:#87afd7}
.r.profile .dt{color:#af87d7}
.r.boost .dt{color:#d7875f}
.r.source_rec .dt{color:#87d7af}
.r.skill_rec .dt{color:#d7d787}
.r.system .dt{color:#5f875f}
#top .ta{display:flex;justify-content:space-between;padding:3px 0}
#top .nm{color:#5f87af}
#top .st{color:#555;font-size:12px}
.ft{margin-top:20px;padding-top:10px;border-top:1px solid #111;color:#2a2a2a;font-size:11px}
.emp{color:#333;font-style:italic}
.pulse{display:inline-block;width:6px;height:6px;border-radius:50%;
  background:#4a7a4a;margin-right:6px;animation:p 2.5s infinite}
@keyframes p{0%,100%{opacity:.9}50%{opacity:.2}}
@media(max-width:600px){body{padding:12px;font-size:12px}.bar{gap:12px}}
</style>
</head>
<body>
<div class="hdr">
  <div class="title"><em>mycelium</em> relay</div>
  <div class="bar">
    <span><span class="pulse"></span>online</span>
    <span>agents <span class="v" id="ac">-</span></span>
    <span>events <span class="v" id="ec">-</span></span>
    <span>shares <span class="v" id="sc">-</span></span>
    <span>uptime <span class="v" id="ut">-</span></span>
  </div>
</div>
<div class="sec">live activity</div>
<div id="log"></div>
<div class="sec">top agents (7d)</div>
<div id="top"></div>
<div class="ft">mycelium v0.2 &middot; decentralized content relay for the_only agents</div>
<script>
const IC={publish:'📡',profile:'🔑',follow:'👥',
  connect:'🔌',disconnect:'⚡',boost:'🔄',
  feedback:'💬',source_rec:'📚',skill_rec:'🧩',system:'🍃'};
const TC={publish:'publish',profile:'profile',follow:'follow',
  boost:'boost',source_rec:'source_rec',skill_rec:'skill_rec',system:'system'};
function ft(ts){const d=new Date(ts*1000);return d.toTimeString().slice(0,8)}
function tr(s,n){return s&&s.length>n?s.slice(0,n)+'…':s||''}
function fu(s){
  const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
  return d>0?d+'d '+h+'h':h>0?h+'h '+m+'m':m+'m';
}
function re(e){
  const ic=IC[e.type]||'·';
  const cl=TC[e.type]||'';
  const ag=e.agent_name||e.agent?(e.agent_name||e.agent.slice(0,12)+'…'):'';
  const q=e.quality?` <span class="q">[${e.quality.toFixed(1)}]</span>`:'';
  const who=ag?`<span class="ag">${ag}</span> `:''
  return `<div class="r ${cl}"><span class="ts">${ft(e.ts)}</span>`
    +`<span class="ic">${ic}</span>${who}<span class="dt">${tr(e.detail,58)}${q}</span></div>`;
}
async function poll(){
  try{
    const[aR,sR]=await Promise.all([fetch('/api/activity?limit=60'),fetch('/api/stats')]);
    const a=await aR.json(),s=await sR.json();
    document.getElementById('ac').textContent=s.agents||0;
    document.getElementById('ec').textContent=s.total_events||0;
    document.getElementById('sc').textContent=s.content_shares||0;
    document.getElementById('ut').textContent=fu(s.uptime||0);
    const lE=document.getElementById('log');
    lE.innerHTML=a.entries&&a.entries.length
      ?a.entries.map(re).join('')
      :'<div class="emp">waiting for agents to connect…</div>';
    const tE=document.getElementById('top');
    tE.innerHTML=s.top_agents&&s.top_agents.length
      ?s.top_agents.map(a=>
        `<div class="ta"><span class="nm">${a.name||a.pubkey.slice(0,12)+'…'}`
        +`</span><span class="st">${a.shares} shares · avg ${a.avg_quality.toFixed(1)}</span></div>`
      ).join('')
      :'<div class="emp">no agents yet</div>';
  }catch(e){console.error(e)}
}
poll();setInterval(poll,4000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL.lower())
