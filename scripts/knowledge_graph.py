#!/usr/bin/env python3
"""
knowledge_graph.py — Persistent Knowledge Graph for the-only v2.
────────────────────────────────────────────────────────────────
Builds and queries a concept graph from curated articles.
Tracks storylines across rituals, detects knowledge clusters,
identifies gaps, and enables cross-ritual intelligence.

Stdlib only. No external deps.

Actions:
  ingest      — Extract concepts + relations from a ritual's articles, merge into graph
  query       — Find concepts, neighbors, paths between concepts
  storylines  — Detect and return active storylines (topics evolving across rituals)
  gaps        — Identify knowledge gaps (weakly connected areas of interest)
  visualize   — Generate Mermaid diagram of a subgraph
  status      — Print graph statistics
  decay       — Apply temporal decay to edge weights (run during maintenance)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

GRAPH_FILE = os.path.expanduser("~/memory/the_only_knowledge_graph.json")

DEFAULT_GRAPH = {
    "version": "2.0",
    "concepts": {},       # concept_id -> {label, first_seen, last_seen, frequency, mastery, domain, aliases}
    "edges": [],          # [{source, target, relation, weight, first_seen, last_seen, ritual_ids}]
    "storylines": [],     # [{id, title, concept_ids, first_ritual, last_ritual, status, arc_summary}]
    "stats": {
        "total_concepts": 0,
        "total_edges": 0,
        "total_rituals_ingested": 0,
        "last_updated": "",
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_graph() -> dict:
    if os.path.exists(GRAPH_FILE):
        try:
            with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[warn] {GRAPH_FILE}: {e}", file=sys.stderr)
    return json.loads(json.dumps(DEFAULT_GRAPH))


def _save_graph(graph: dict) -> None:
    os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
    graph["stats"]["total_concepts"] = len(graph["concepts"])
    graph["stats"]["total_edges"] = len(graph["edges"])
    graph["stats"]["last_updated"] = _now_iso()
    tmp = GRAPH_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, GRAPH_FILE)


def _concept_id(label: str) -> str:
    """Normalize a concept label to a stable ID."""
    return label.lower().strip().replace(" ", "_").replace("-", "_")


# ── Actions ──────────────────────────────────────────────────────────────

def action_ingest(data_str: str) -> None:
    """Ingest concepts and relations from a ritual.

    Expected JSON format:
    {
      "ritual_id": 47,
      "items": [
        {
          "title": "...",
          "concepts": ["concept1", "concept2"],
          "relations": [
            {"source": "concept1", "target": "concept2", "relation": "enables"},
          ],
          "domain": "tech",
          "mastery_signals": {"concept1": "introduced", "concept2": "deepened"}
        }
      ]
    }
    """
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        print("error: --data must be valid JSON", file=sys.stderr)
        sys.exit(1)

    graph = _load_graph()
    ritual_id = data.get("ritual_id", 0)
    now = _now_iso()

    all_ritual_concepts = set()

    for item in data.get("items", []):
        domain = item.get("domain", "general")
        concepts = item.get("concepts", [])
        relations = item.get("relations", [])
        mastery = item.get("mastery_signals", {})

        # Upsert concepts
        for c in concepts:
            cid = _concept_id(c)
            all_ritual_concepts.add(cid)
            if cid in graph["concepts"]:
                node = graph["concepts"][cid]
                node["frequency"] = node.get("frequency", 0) + 1
                node["last_seen"] = now
                # Update mastery if signal provided
                if c in mastery:
                    node["mastery"] = _update_mastery(
                        node.get("mastery", "unknown"), mastery[c]
                    )
            else:
                graph["concepts"][cid] = {
                    "label": c,
                    "first_seen": now,
                    "last_seen": now,
                    "frequency": 1,
                    "mastery": mastery.get(c, "introduced"),
                    "domain": domain,
                    "aliases": [],
                }

        # Upsert edges
        for rel in relations:
            src = _concept_id(rel.get("source", ""))
            tgt = _concept_id(rel.get("target", ""))
            rtype = rel.get("relation", "related_to")
            if not src or not tgt:
                continue

            existing = _find_edge(graph["edges"], src, tgt, rtype)
            if existing is not None:
                edge = graph["edges"][existing]
                edge["weight"] = edge.get("weight", 1.0) + 0.5
                edge["last_seen"] = now
                if ritual_id not in edge.get("ritual_ids", []):
                    edge.setdefault("ritual_ids", []).append(ritual_id)
            else:
                graph["edges"].append({
                    "source": src,
                    "target": tgt,
                    "relation": rtype,
                    "weight": 1.0,
                    "first_seen": now,
                    "last_seen": now,
                    "ritual_ids": [ritual_id],
                })

    # ── Storyline detection ──
    _update_storylines(graph, all_ritual_concepts, ritual_id)

    graph["stats"]["total_rituals_ingested"] = graph["stats"].get(
        "total_rituals_ingested", 0
    ) + 1

    _save_graph(graph)
    print(f"ok: ingested {len(all_ritual_concepts)} concepts from ritual {ritual_id}")


def _update_mastery(current: str, signal: str) -> str:
    """Progress mastery level based on new signal."""
    levels = ["unknown", "introduced", "familiar", "understood", "mastered"]
    cur_idx = levels.index(current) if current in levels else 0
    sig_idx = levels.index(signal) if signal in levels else 0
    # Mastery can only go up, never down from a single signal
    return levels[max(cur_idx, sig_idx)]


def _find_edge(edges: list, src: str, tgt: str, rtype: str) -> int | None:
    """Find an existing edge index, treating (src,tgt) and (tgt,src) as equivalent for 'related_to'."""
    for i, e in enumerate(edges):
        if e["relation"] == rtype:
            if (e["source"] == src and e["target"] == tgt) or (
                rtype == "related_to"
                and e["source"] == tgt
                and e["target"] == src
            ):
                return i
    return None


def _update_storylines(
    graph: dict, ritual_concepts: set[str], ritual_id: int
) -> None:
    """Detect and update storylines — topics that appear across 3+ rituals."""
    storylines = graph.get("storylines", [])

    # Update existing storylines
    for sl in storylines:
        if sl.get("status") == "closed":
            continue
        overlap = set(sl.get("concept_ids", [])) & ritual_concepts
        if overlap:
            sl["last_ritual"] = ritual_id
            sl["ritual_count"] = sl.get("ritual_count", 1) + 1
            # Add new concepts that co-occur with storyline concepts
            for c in ritual_concepts:
                neighbors = _get_neighbors(graph, c)
                if neighbors & set(sl["concept_ids"]) and c not in sl["concept_ids"]:
                    sl["concept_ids"].append(c)

    # Detect new potential storylines from concept clusters
    # A storyline candidate = 3+ concepts that co-occur in this ritual
    # and have appeared in 2+ previous rituals
    if len(ritual_concepts) >= 3:
        recurring = {
            c for c in ritual_concepts
            if graph["concepts"].get(c, {}).get("frequency", 0) >= 3
        }
        if len(recurring) >= 2:
            # Check if this cluster is already a storyline
            existing_ids = {
                frozenset(sl["concept_ids"]) for sl in storylines
                if sl.get("status") != "closed"
            }
            new_cluster = frozenset(recurring)
            is_new = all(
                len(new_cluster & existing) / max(len(new_cluster | existing), 1) < 0.5
                for existing in existing_ids
            )
            if is_new and len(recurring) >= 2:
                storylines.append({
                    "id": f"sl_{ritual_id}_{len(storylines)}",
                    "title": "",  # Claude fills this in based on concepts
                    "concept_ids": list(recurring),
                    "first_ritual": ritual_id,
                    "last_ritual": ritual_id,
                    "ritual_count": 1,
                    "status": "active",
                    "arc_summary": "",
                })

    # Close stale storylines (no activity for 10+ rituals)
    for sl in storylines:
        if sl.get("status") == "active":
            gap = ritual_id - sl.get("last_ritual", ritual_id)
            if gap > 10:
                sl["status"] = "dormant"

    graph["storylines"] = storylines


def _get_neighbors(graph: dict, concept_id: str) -> set[str]:
    """Get all concepts directly connected to a given concept."""
    neighbors = set()
    for edge in graph.get("edges", []):
        if edge["source"] == concept_id:
            neighbors.add(edge["target"])
        elif edge["target"] == concept_id:
            neighbors.add(edge["source"])
    return neighbors


def action_query(query_str: str) -> None:
    """Query the knowledge graph.

    JSON format:
    {"concept": "X"}                          — get concept + neighbors
    {"path": ["X", "Y"]}                      — find shortest path
    {"cluster": "X"}                          — get concept cluster (2-hop neighborhood)
    {"domain": "tech"}                        — list concepts in domain
    {"recent": 5}                             — most recently active concepts
    """
    try:
        q = json.loads(query_str)
    except json.JSONDecodeError:
        print("error: --query must be valid JSON", file=sys.stderr)
        sys.exit(1)

    graph = _load_graph()

    if "concept" in q:
        cid = _concept_id(q["concept"])
        node = graph["concepts"].get(cid)
        if not node:
            print(json.dumps({"error": f"concept '{q['concept']}' not found"}))
            return
        neighbors = []
        for edge in graph["edges"]:
            if edge["source"] == cid:
                neighbors.append({
                    "concept": graph["concepts"].get(edge["target"], {}).get("label", edge["target"]),
                    "relation": edge["relation"],
                    "weight": edge["weight"],
                })
            elif edge["target"] == cid:
                neighbors.append({
                    "concept": graph["concepts"].get(edge["source"], {}).get("label", edge["source"]),
                    "relation": edge["relation"],
                    "weight": edge["weight"],
                })
        result = {"concept": node, "neighbors": neighbors}
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif "path" in q:
        path_endpoints = q["path"]
        if len(path_endpoints) != 2:
            print(json.dumps({"error": "path requires exactly 2 concepts"}))
            return
        src = _concept_id(path_endpoints[0])
        tgt = _concept_id(path_endpoints[1])
        path = _bfs_path(graph, src, tgt)
        if path:
            labels = [graph["concepts"].get(c, {}).get("label", c) for c in path]
            print(json.dumps({"path": labels, "length": len(path) - 1}))
        else:
            print(json.dumps({"path": None, "message": "no path found"}))

    elif "cluster" in q:
        cid = _concept_id(q["cluster"])
        hop1 = _get_neighbors(graph, cid)
        hop2 = set()
        for n in hop1:
            hop2 |= _get_neighbors(graph, n)
        cluster = {cid} | hop1 | hop2
        concepts = {
            c: graph["concepts"][c]
            for c in cluster if c in graph["concepts"]
        }
        print(json.dumps({"cluster_center": q["cluster"], "size": len(concepts), "concepts": concepts}, indent=2, ensure_ascii=False))

    elif "domain" in q:
        domain = q["domain"].lower()
        matches = {
            cid: node for cid, node in graph["concepts"].items()
            if node.get("domain", "").lower() == domain
        }
        print(json.dumps({"domain": domain, "count": len(matches), "concepts": matches}, indent=2, ensure_ascii=False))

    elif "recent" in q:
        n = int(q["recent"])
        by_time = sorted(
            graph["concepts"].items(),
            key=lambda x: x[1].get("last_seen", ""),
            reverse=True,
        )[:n]
        print(json.dumps(
            {"recent": [{**v, "id": k} for k, v in by_time]},
            indent=2, ensure_ascii=False,
        ))


def _bfs_path(graph: dict, src: str, tgt: str) -> list[str] | None:
    """BFS shortest path between two concepts."""
    if src == tgt:
        return [src]
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph["edges"]:
        adj[edge["source"]].append(edge["target"])
        adj[edge["target"]].append(edge["source"])

    visited = {src}
    queue = [(src, [src])]
    while queue:
        current, path = queue.pop(0)
        for neighbor in adj[current]:
            if neighbor == tgt:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None


def action_storylines() -> None:
    """Return active and dormant storylines."""
    graph = _load_graph()
    storylines = graph.get("storylines", [])

    active = [s for s in storylines if s.get("status") == "active"]
    dormant = [s for s in storylines if s.get("status") == "dormant"]

    for sl in active + dormant:
        # Enrich with concept labels
        sl["concept_labels"] = [
            graph["concepts"].get(c, {}).get("label", c)
            for c in sl.get("concept_ids", [])
        ]

    result = {
        "active": active,
        "dormant": dormant,
        "total": len(storylines),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


def action_gaps(interests_str: str) -> None:
    """Identify knowledge gaps based on user interests.

    --interests: comma-separated list of interest areas
    Gaps are interests with few concepts or weak connections in the graph.
    """
    interests = [i.strip().lower() for i in interests_str.split(",") if i.strip()]
    graph = _load_graph()

    gaps = []
    for interest in interests:
        # Find concepts related to this interest
        related = []
        for cid, node in graph["concepts"].items():
            label = node.get("label", "").lower()
            domain = node.get("domain", "").lower()
            if interest in label or interest in domain:
                related.append(node)

        if not related:
            gaps.append({
                "interest": interest,
                "gap_type": "unexplored",
                "description": f"No concepts found for '{interest}' — this domain is entirely unexplored",
                "severity": "high",
            })
        elif len(related) < 3:
            gaps.append({
                "interest": interest,
                "gap_type": "shallow",
                "description": f"Only {len(related)} concepts — surface-level coverage",
                "severity": "medium",
                "existing_concepts": [r["label"] for r in related],
            })
        else:
            # Check mastery distribution
            mastery_dist = defaultdict(int)
            for r in related:
                mastery_dist[r.get("mastery", "unknown")] += 1
            if mastery_dist.get("introduced", 0) > len(related) * 0.6:
                gaps.append({
                    "interest": interest,
                    "gap_type": "superficial",
                    "description": f"{len(related)} concepts but >60% at 'introduced' level — breadth without depth",
                    "severity": "medium",
                    "mastery_distribution": dict(mastery_dist),
                })

    print(json.dumps({"gaps": gaps, "total_interests": len(interests)}, indent=2, ensure_ascii=False))


def action_visualize(query_str: str) -> None:
    """Generate a Mermaid diagram for a subgraph.

    --query JSON: {"center": "concept", "hops": 2} or {"storyline": "sl_id"}
    """
    try:
        q = json.loads(query_str)
    except json.JSONDecodeError:
        print("error: --query must be valid JSON", file=sys.stderr)
        sys.exit(1)

    graph = _load_graph()
    nodes_to_include = set()
    edges_to_include = []

    if "center" in q:
        cid = _concept_id(q["center"])
        hops = q.get("hops", 2)
        current_layer = {cid}
        nodes_to_include = {cid}
        for _ in range(hops):
            next_layer = set()
            for n in current_layer:
                next_layer |= _get_neighbors(graph, n)
            nodes_to_include |= next_layer
            current_layer = next_layer

    elif "storyline" in q:
        sl_id = q["storyline"]
        for sl in graph.get("storylines", []):
            if sl["id"] == sl_id:
                nodes_to_include = set(sl.get("concept_ids", []))
                break

    # Collect relevant edges
    for edge in graph["edges"]:
        if edge["source"] in nodes_to_include and edge["target"] in nodes_to_include:
            edges_to_include.append(edge)

    # Generate Mermaid
    lines = ["graph TD"]
    for nid in nodes_to_include:
        node = graph["concepts"].get(nid, {})
        label = node.get("label", nid)
        mastery = node.get("mastery", "unknown")
        style_class = {"mastered": ":::mastered", "understood": ":::understood",
                       "familiar": ":::familiar", "introduced": ":::introduced"}.get(mastery, "")
        lines.append(f'    {nid}["{label}"]{style_class}')

    for edge in edges_to_include:
        rel = edge.get("relation", "")
        weight = edge.get("weight", 1)
        arrow = "==>" if weight >= 3 else "-->" if weight >= 1.5 else "-.->"
        if rel and rel != "related_to":
            lines.append(f'    {edge["source"]} {arrow}|{rel}| {edge["target"]}')
        else:
            lines.append(f'    {edge["source"]} {arrow} {edge["target"]}')

    lines.extend([
        "",
        "    classDef mastered fill:#00d4aa,color:#0a0a0f,stroke:#00d4aa",
        "    classDef understood fill:#8b5cf6,color:#f0f0f5,stroke:#8b5cf6",
        "    classDef familiar fill:#f0a500,color:#0a0a0f,stroke:#f0a500",
        "    classDef introduced fill:#606078,color:#f0f0f5,stroke:#606078",
    ])

    mermaid = "\n".join(lines)
    print(mermaid)


def action_decay() -> None:
    """Apply temporal decay to edge weights. Run during maintenance."""
    graph = _load_graph()
    now = datetime.now(timezone.utc)
    decayed = 0

    for edge in graph["edges"]:
        last_seen = edge.get("last_seen", "")
        if not last_seen:
            continue
        try:
            last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            days_ago = (now - last_dt).days
            if days_ago > 30:
                decay_factor = math.exp(-0.01 * (days_ago - 30))
                edge["weight"] = round(edge["weight"] * decay_factor, 2)
                decayed += 1
        except (ValueError, TypeError):
            continue

    # Remove edges with negligible weight
    before = len(graph["edges"])
    graph["edges"] = [e for e in graph["edges"] if e.get("weight", 0) > 0.1]
    removed = before - len(graph["edges"])

    _save_graph(graph)
    print(f"ok: decayed {decayed} edges, removed {removed} negligible edges")


def action_status() -> None:
    """Print graph statistics."""
    graph = _load_graph()
    stats = graph["stats"]
    concepts = graph["concepts"]
    storylines = graph.get("storylines", [])

    # Domain distribution
    domains = defaultdict(int)
    mastery_dist = defaultdict(int)
    for node in concepts.values():
        domains[node.get("domain", "unknown")] += 1
        mastery_dist[node.get("mastery", "unknown")] += 1

    active_sl = sum(1 for s in storylines if s.get("status") == "active")

    print(f"=== Knowledge Graph Status ===")
    print(f"Concepts: {stats.get('total_concepts', 0)}")
    print(f"Edges: {stats.get('total_edges', 0)}")
    print(f"Rituals ingested: {stats.get('total_rituals_ingested', 0)}")
    print(f"Active storylines: {active_sl}")
    print(f"Last updated: {stats.get('last_updated', 'never')}")
    print(f"\nDomains: {dict(domains)}")
    print(f"Mastery: {dict(mastery_dist)}")


def main():
    parser = argparse.ArgumentParser(description="The ONLY — Knowledge Graph")
    parser.add_argument("--action", required=True,
                        choices=["ingest", "query", "storylines", "gaps", "visualize", "decay", "status"])
    parser.add_argument("--data", type=str, help="JSON data for ingest")
    parser.add_argument("--query", type=str, help="JSON query for query/visualize")
    parser.add_argument("--interests", type=str, help="Comma-separated interests for gaps")

    args = parser.parse_args()

    if args.action == "ingest":
        if not args.data:
            print("error: --data required for ingest", file=sys.stderr)
            sys.exit(1)
        action_ingest(args.data)
    elif args.action == "query":
        if not args.query:
            print("error: --query required", file=sys.stderr)
            sys.exit(1)
        action_query(args.query)
    elif args.action == "storylines":
        action_storylines()
    elif args.action == "gaps":
        if not args.interests:
            print("error: --interests required", file=sys.stderr)
            sys.exit(1)
        action_gaps(args.interests)
    elif args.action == "visualize":
        if not args.query:
            print("error: --query required", file=sys.stderr)
            sys.exit(1)
        action_visualize(args.query)
    elif args.action == "decay":
        action_decay()
    elif args.action == "status":
        action_status()


if __name__ == "__main__":
    main()
