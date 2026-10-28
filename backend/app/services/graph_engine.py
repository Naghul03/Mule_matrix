"""
Temporal Graph Engine using NetworkX.

Builds directed graphs from MySQL transaction records and provides:
- Forward/backward tracing
- Multi-hop traversal with time-window filtering
- Fan-in / fan-out detection
- Cycle detection
- Convergence detection
- Connected component analysis
- Potential central-beneficiary ranking
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import networkx as nx


# ─────────────────────────────────────────────────────────────────────────────
# Graph node and edge builders
# ─────────────────────────────────────────────────────────────────────────────

def build_graph(transactions: list[dict]) -> nx.DiGraph:
    """
    Build a directed graph from a list of canonical transaction dicts.
    Each dict should contain: id, sender_account_ref, receiver_account_ref,
    amount, currency, timestamp_utc (str or datetime), source_bank_id,
    destination_bank_id, status, is_suspicious, risk_score.
    """
    G = nx.DiGraph()

    for txn in transactions:
        sender = txn.get("sender_account_ref") or txn.get("sender_id")
        receiver = txn.get("receiver_account_ref") or txn.get("receiver_id")
        if not sender or not receiver:
            continue

        ts = txn.get("timestamp_utc")
        if isinstance(ts, str):
            try:
                from dateutil import parser
                ts = parser.parse(ts)
            except Exception:
                ts = None
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Add nodes if not present
        for node in (sender, receiver):
            if not G.has_node(node):
                G.add_node(node, node_type="account", is_suspicious=False, risk_score=0.0)

        amount = float(txn.get("amount", 0))
        G.add_edge(
            sender,
            receiver,
            txn_id=txn.get("id", ""),
            transaction_ref=txn.get("transaction_ref", ""),
            amount=amount,
            currency=txn.get("currency", "INR"),
            timestamp_utc=ts,
            source_bank_id=txn.get("source_bank_id", ""),
            destination_bank_id=txn.get("destination_bank_id", ""),
            status=txn.get("status", "COMPLETED"),
            is_suspicious=txn.get("is_suspicious", False),
            risk_score=float(txn.get("risk_score", 0)),
            provenance_id=txn.get("provenance_id", ""),
        )

    return G


# ─────────────────────────────────────────────────────────────────────────────
# Tracing
# ─────────────────────────────────────────────────────────────────────────────

def forward_trace(
    G: nx.DiGraph,
    start_node: str,
    max_depth: int = 4,
    time_window: tuple[datetime, datetime] | None = None,
    min_amount: float | None = None,
) -> dict[str, Any]:
    """
    Trace all paths forward (downstream) from start_node.
    Returns discovered nodes, edges, and path info.
    """
    visited_nodes = set()
    visited_edges = []
    discovery_depth: dict[str, int] = {start_node: 0}
    queue = [(start_node, 0)]

    while queue:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for successor in G.successors(current):
            edge_data = G.get_edge_data(current, successor)
            if not _edge_passes_filters(edge_data, time_window, min_amount):
                continue
            visited_edges.append({
                "from": current, "to": successor,
                "depth": depth + 1, **edge_data,
                "timestamp_utc": _ts_to_str(edge_data.get("timestamp_utc")),
            })
            if successor not in discovery_depth:
                discovery_depth[successor] = depth + 1
                queue.append((successor, depth + 1))
            visited_nodes.add(successor)

    return {
        "direction": "forward",
        "start_node": start_node,
        "nodes": list(visited_nodes | {start_node}),
        "edges": visited_edges,
        "discovery_depth": discovery_depth,
    }


def backward_trace(
    G: nx.DiGraph,
    start_node: str,
    max_depth: int = 4,
    time_window: tuple[datetime, datetime] | None = None,
    min_amount: float | None = None,
) -> dict[str, Any]:
    """
    Trace all paths backward (upstream) from start_node.
    Traversal follows edges in reverse. Transaction direction is preserved in output.
    """
    visited_nodes = set()
    visited_edges = []
    discovery_depth: dict[str, int] = {start_node: 0}
    queue = [(start_node, 0)]

    while queue:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for predecessor in G.predecessors(current):
            edge_data = G.get_edge_data(predecessor, current)
            if not _edge_passes_filters(edge_data, time_window, min_amount):
                continue
            visited_edges.append({
                "from": predecessor, "to": current,  # preserve actual direction
                "depth": depth + 1, **edge_data,
                "timestamp_utc": _ts_to_str(edge_data.get("timestamp_utc")),
                "traversal_direction": "backward",
            })
            if predecessor not in discovery_depth:
                discovery_depth[predecessor] = depth + 1
                queue.append((predecessor, depth + 1))
            visited_nodes.add(predecessor)

    return {
        "direction": "backward",
        "start_node": start_node,
        "nodes": list(visited_nodes | {start_node}),
        "edges": visited_edges,
        "discovery_depth": discovery_depth,
    }


def multi_hop_trace(
    G: nx.DiGraph,
    start_nodes: list[str],
    max_depth: int = 4,
    time_window: tuple[datetime, datetime] | None = None,
    min_amount: float | None = None,
) -> dict[str, Any]:
    """
    Forward trace from multiple starting nodes, merging results.
    Used for Scenario 3 backward discovery → then forward from discovered nodes.
    """
    all_nodes = set()
    all_edges = []
    all_depths: dict[str, int] = {}

    for start in start_nodes:
        result = forward_trace(G, start, max_depth, time_window, min_amount)
        all_nodes.update(result["nodes"])
        all_edges.extend(result["edges"])
        for node, depth in result["discovery_depth"].items():
            if node not in all_depths or all_depths[node] > depth:
                all_depths[node] = depth

    # Deduplicate edges by txn_id
    seen_txn_ids = set()
    unique_edges = []
    for e in all_edges:
        tid = e.get("txn_id")
        if tid and tid not in seen_txn_ids:
            seen_txn_ids.add(tid)
            unique_edges.append(e)
        elif not tid:
            unique_edges.append(e)

    return {
        "direction": "multi_hop",
        "start_nodes": start_nodes,
        "nodes": list(all_nodes),
        "edges": unique_edges,
        "discovery_depth": all_depths,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Detection functions
# ─────────────────────────────────────────────────────────────────────────────

def detect_fan_out(G: nx.DiGraph, threshold: int = 3) -> list[dict]:
    """Find accounts sending to many destinations — fan-out pattern."""
    results = []
    for node in G.nodes():
        out_degree = G.out_degree(node)
        if out_degree >= threshold:
            successors = list(G.successors(node))
            total_out = sum(G[node][s].get("amount", 0) for s in successors)
            results.append({
                "account": node,
                "out_degree": out_degree,
                "destinations": successors,
                "total_outgoing": total_out,
                "pattern": "FAN_OUT",
            })
    return sorted(results, key=lambda x: x["out_degree"], reverse=True)


def detect_fan_in(G: nx.DiGraph, threshold: int = 3) -> list[dict]:
    """Find accounts receiving from many sources — fan-in / convergence."""
    results = []
    for node in G.nodes():
        in_degree = G.in_degree(node)
        if in_degree >= threshold:
            predecessors = list(G.predecessors(node))
            total_in = sum(G[p][node].get("amount", 0) for p in predecessors)
            results.append({
                "account": node,
                "in_degree": in_degree,
                "sources": predecessors,
                "total_incoming": total_in,
                "pattern": "FAN_IN",
            })
    return sorted(results, key=lambda x: x["in_degree"], reverse=True)


def detect_cycles(G: nx.DiGraph) -> list[list[str]]:
    """Detect all cycles in the graph."""
    try:
        return list(nx.simple_cycles(G))
    except Exception:
        return []


def detect_convergence(
    G: nx.DiGraph,
    suspicious_nodes: set[str],
    time_window_hours: float = 48.0,
) -> list[dict]:
    """
    Detect temporal convergence: multiple suspicious paths reaching the same
    destination within a configurable time window.
    """
    destination_arrivals: dict[str, list[dict]] = {}

    for u, v, data in G.edges(data=True):
        if u in suspicious_nodes:
            ts = data.get("timestamp_utc")
            if ts is None:
                continue
            if ts not in destination_arrivals:
                destination_arrivals[v] = []
            destination_arrivals[v].append({
                "from": u, "to": v,
                "timestamp_utc": ts,
                "amount": data.get("amount", 0),
                "txn_id": data.get("txn_id", ""),
            })

    convergence_events = []
    for dest, arrivals in destination_arrivals.items():
        if len(arrivals) < 2:
            continue
        # Check if any two arrivals are within time_window_hours
        arrivals_sorted = sorted(arrivals, key=lambda x: x["timestamp_utc"])
        for i in range(len(arrivals_sorted)):
            for j in range(i + 1, len(arrivals_sorted)):
                t1 = arrivals_sorted[i]["timestamp_utc"]
                t2 = arrivals_sorted[j]["timestamp_utc"]
                if t1 and t2:
                    diff = abs((t2 - t1).total_seconds()) / 3600
                    if diff <= time_window_hours:
                        convergence_events.append({
                            "destination": dest,
                            "arrivals": [arrivals_sorted[i], arrivals_sorted[j]],
                            "time_gap_hours": round(diff, 2),
                            "pattern": "TEMPORAL_CONVERGENCE",
                        })
                        break

    return convergence_events


def rank_central_beneficiaries(
    G: nx.DiGraph,
    suspicious_nodes: set[str],
    starting_node: str | None = None,
) -> list[dict]:
    """
    Rank potential central beneficiaries using multiple signals:
    - Suspicious inflow count and value
    - Source diversity (number of unique suspicious predecessors)
    - Temporal proximity of inflows
    - Outflow ratio (low outflow from recipient = potential end-point)
    - PageRank contribution from suspicious subgraph
    """
    if len(G.nodes()) == 0:
        return []

    # PageRank on full graph
    try:
        pr = nx.pagerank(G, alpha=0.85)
    except Exception:
        pr = {n: 0.0 for n in G.nodes()}

    candidates = {}
    for node in G.nodes():
        if node in suspicious_nodes:
            continue  # skip nodes already known to be in the chain

        # Inflows from suspicious nodes
        suspicious_inflows = []
        for pred in G.predecessors(node):
            if pred in suspicious_nodes or pred == starting_node:
                edge = G[pred][node]
                suspicious_inflows.append({
                    "from": pred,
                    "amount": edge.get("amount", 0),
                    "timestamp_utc": _ts_to_str(edge.get("timestamp_utc")),
                })

        if not suspicious_inflows:
            continue

        total_suspicious_in = sum(x["amount"] for x in suspicious_inflows)
        source_diversity = len(set(x["from"] for x in suspicious_inflows))
        total_out = sum(G[node][s].get("amount", 0) for s in G.successors(node))
        out_ratio = total_out / total_suspicious_in if total_suspicious_in > 0 else 0
        page_rank_score = pr.get(node, 0.0)

        # Composite score (explainable weights)
        score = (
            min(total_suspicious_in / 1_000_000, 1.0) * 30  # value weight
            + min(source_diversity / 5, 1.0) * 25            # diversity weight
            + (1 - min(out_ratio, 1.0)) * 20                 # retention weight
            + page_rank_score * 1000 * 25                    # centrality weight
        )

        candidates[node] = {
            "account": node,
            "suspicious_inflows": suspicious_inflows,
            "total_suspicious_inflow": round(total_suspicious_in, 2),
            "source_diversity": source_diversity,
            "total_outflow": round(total_out, 2),
            "outflow_ratio": round(out_ratio, 4),
            "pagerank": round(page_rank_score, 6),
            "composite_score": round(score, 2),
            "evidence": [
                f"Received {len(suspicious_inflows)} inflow(s) from suspicious network",
                f"Total suspicious inflow: ₹{total_suspicious_in:,.2f}",
                f"Source diversity: {source_diversity} unique source(s)",
                f"Outflow ratio: {out_ratio:.2%} of suspicious inflow",
                f"PageRank: {page_rank_score:.6f}",
            ],
        }

    ranked = sorted(candidates.values(), key=lambda x: x["composite_score"], reverse=True)
    return ranked


def get_connected_components(G: nx.DiGraph) -> list[list[str]]:
    """Return weakly connected components."""
    return [list(c) for c in nx.weakly_connected_components(G)]


# ─────────────────────────────────────────────────────────────────────────────
# Graph export (for Cytoscape.js)
# ─────────────────────────────────────────────────────────────────────────────

def export_for_cytoscape(
    G: nx.DiGraph,
    suspicious_nodes: set[str] | None = None,
    highlighted_path: list[str] | None = None,
    account_details: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Export graph to Cytoscape.js elements format."""
    suspicious_nodes = suspicious_nodes or set()
    highlighted_path = highlighted_path or []
    account_details = account_details or {}

    elements = []

    for node in G.nodes():
        data = G.nodes[node]
        acc = account_details.get(node, {})
        elements.append({
            "data": {
                "id": node,
                "label": acc.get("owner_name", node),
                "node_type": "account",
                "bank_code": acc.get("bank_code", ""),
                "is_suspicious": node in suspicious_nodes,
                "in_highlighted_path": node in highlighted_path,
                "risk_score": acc.get("risk_score", 0),
                "balance": acc.get("balance", 0),
            },
            "classes": _node_classes(node, suspicious_nodes, highlighted_path),
        })

    # Deduplicate edges (DiGraph allows one edge per u→v pair)
    seen = set()
    for u, v, data in G.edges(data=True):
        key = (u, v, data.get("txn_id", ""))
        if key in seen:
            continue
        seen.add(key)
        elements.append({
            "data": {
                "id": f"{u}__{v}__{data.get('txn_id', '')}",
                "source": u,
                "target": v,
                "label": f"₹{data.get('amount', 0):,.0f}",
                "amount": data.get("amount", 0),
                "currency": data.get("currency", "INR"),
                "timestamp_utc": _ts_to_str(data.get("timestamp_utc")),
                "txn_id": data.get("txn_id", ""),
                "is_suspicious": data.get("is_suspicious", False),
                "status": data.get("status", "COMPLETED"),
                "source_bank_id": data.get("source_bank_id", ""),
            },
            "classes": "transaction-edge" + (" suspicious" if data.get("is_suspicious") else ""),
        })

    return {"elements": elements, "node_count": len(G.nodes()), "edge_count": len(G.edges())}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _edge_passes_filters(
    edge_data: dict,
    time_window: tuple[datetime, datetime] | None,
    min_amount: float | None,
) -> bool:
    if min_amount is not None:
        if edge_data.get("amount", 0) < min_amount:
            return False
    if time_window is not None:
        ts = edge_data.get("timestamp_utc")
        if ts and isinstance(ts, datetime):
            lo, hi = time_window
            if not (lo <= ts <= hi):
                return False
    return True


def _ts_to_str(ts: Any) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts)


def _node_classes(node: str, suspicious: set[str], path: list[str]) -> str:
    classes = []
    if node in suspicious:
        classes.append("suspicious")
    if node in path:
        classes.append("highlighted")
    return " ".join(classes)
