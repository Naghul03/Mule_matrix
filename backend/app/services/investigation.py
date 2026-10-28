"""
Investigation Service — orchestrates the full investigation pipeline:
1. Receives trigger (reported fraud or automatic)
2. Queries bank adapters for relevant records
3. Builds temporal graph
4. Runs behavioural detection
5. Runs provenance tracking
6. Ranks central beneficiaries
7. Creates alerts with evidence
8. Persists results to database
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models import (
    Transaction, Account, Bank, Investigation, RiskAlert,
    ProvenanceRecord, ProvenanceMovement, AuditEvent,
    AlertSeverity, AlertStatus, InvestigationStatus, InvestigationEntryType,
    ProvenanceMode, AllocationMethod, ProvenanceStatus,
)
from app.services.graph_engine import (
    build_graph, forward_trace, backward_trace,
    detect_fan_out, detect_fan_in, detect_cycles,
    detect_convergence, rank_central_beneficiaries,
    export_for_cytoscape,
)
from app.services.detection import (
    compute_dwell_time, compute_pass_through_ratio,
    compute_velocity, compute_counterparty_count,
    compute_amount_deviation, fuse_risk,
)


async def create_investigation(
    db: AsyncSession,
    entry_type: str,
    starting_transaction_id: str | None = None,
    starting_account_id: str | None = None,
    scenario_run_id: str | None = None,
    scenario_id: str | None = None,
    title: str | None = None,
) -> Investigation:
    inv = Investigation(
        id=str(uuid.uuid4()),
        entry_type=InvestigationEntryType(entry_type),
        starting_transaction_id=starting_transaction_id,
        starting_account_id=starting_account_id,
        scenario_run_id=scenario_run_id,
        scenario_id=scenario_id,
        status=InvestigationStatus.OPEN,
        title=title or f"Investigation {datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
    )
    db.add(inv)
    await db.flush()

    await _log_audit(db, "INVESTIGATION_CREATED", "investigation", inv.id,
                     f"Investigation created: entry_type={entry_type}")
    return inv


async def run_investigation(
    db: AsyncSession,
    investigation_id: str,
    max_depth_forward: int = 4,
    max_depth_backward: int = 4,
    time_window_days: int = 60,
) -> dict:
    """
    Full investigation pipeline: graph construction, behavioural analysis,
    alert generation.
    """
    # Load investigation
    result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
    inv = result.scalar_one_or_none()
    if inv is None:
        raise ValueError(f"Investigation {investigation_id} not found")

    inv.status = InvestigationStatus.IN_PROGRESS
    inv.max_depth_forward = max_depth_forward
    inv.max_depth_backward = max_depth_backward
    inv.time_window_days = time_window_days

    # Determine starting account
    starting_account_ref = None
    starting_txn = None
    if inv.starting_transaction_id:
        txn_result = await db.execute(
            select(Transaction).where(Transaction.id == inv.starting_transaction_id)
        )
        starting_txn = txn_result.scalar_one_or_none()
        if starting_txn:
            starting_account_ref = starting_txn.sender_account_ref

    elif inv.starting_account_id:
        acc_result = await db.execute(
            select(Account).where(Account.id == inv.starting_account_id)
        )
        acc = acc_result.scalar_one_or_none()
        if acc:
            starting_account_ref = acc.account_ref

    if not starting_account_ref:
        raise ValueError("Cannot determine starting account for investigation")

    # Fetch all transactions within time window relevant to the scenario run
    time_lo = datetime.now(timezone.utc) - timedelta(days=time_window_days)
    query = select(Transaction).where(Transaction.timestamp_utc >= time_lo)
    if inv.scenario_run_id:
        query = query.where(Transaction.scenario_run_id == inv.scenario_run_id)
    query = query.order_by(Transaction.timestamp_utc)

    txn_result = await db.execute(query)
    all_txns = txn_result.scalars().all()

    # Build graph
    txn_dicts = [_txn_to_dict(t) for t in all_txns]
    G = build_graph(txn_dicts)

    # Forward trace from starting account
    forward_result = forward_trace(G, starting_account_ref, max_depth=max_depth_forward)
    suspicious_nodes = set(forward_result["nodes"])
    suspicious_nodes.discard(starting_account_ref)

    # For each suspicious intermediate, run backward trace
    backward_results = []
    for node in list(suspicious_nodes):
        bwd = backward_trace(G, node, max_depth=max_depth_backward)
        backward_results.append(bwd)
        for n in bwd["nodes"]:
            suspicious_nodes.add(n)

    # Detect patterns
    fan_out_list = detect_fan_out(G, threshold=3)
    fan_in_list = detect_fan_in(G, threshold=3)
    cycles = detect_cycles(G)
    convergence_events = detect_convergence(G, suspicious_nodes)
    central_candidates = rank_central_beneficiaries(G, suspicious_nodes, starting_account_ref)

    # Build Cytoscape graph export
    cyto_data = export_for_cytoscape(G, suspicious_nodes)
    inv.graph_data = json.dumps(cyto_data)

    # Behavioural analysis per suspicious account
    alerts_created = []
    for node in suspicious_nodes:
        node_incoming = [t for t in txn_dicts if t.get("receiver_account_ref") == node]
        node_outgoing = [t for t in txn_dicts if t.get("sender_account_ref") == node]

        if not node_incoming and not node_outgoing:
            continue

        # Dwell time
        dwell = compute_dwell_time(node_incoming, node_outgoing)
        # Pass-through
        ptr = compute_pass_through_ratio(node_incoming, node_outgoing)
        # Velocity
        vel = compute_velocity(node_incoming + node_outgoing, window_hours=48)
        # Counterparty
        cp = compute_counterparty_count(node_incoming + node_outgoing, node, window_days=30)

        features = {
            **dwell,
            **ptr,
            **vel,
            **cp,
            "fan_out": any(r["account"] == node for r in fan_out_list),
            "fan_in": any(r["account"] == node for r in fan_in_list),
            "cycle_detected": any(node in cycle for cycle in cycles),
            "temporal_convergence": any(e["destination"] == node for e in convergence_events),
        }

        risk_result = fuse_risk(features)
        if risk_result["risk_score"] >= 20:  # only create alerts worth noting
            alert = await _create_alert(
                db, inv, node, risk_result,
                title=f"Suspicious pattern on account {node}",
                alert_type="BEHAVIOURAL_PATTERN",
            )
            alerts_created.append(alert)

    # Create convergence alerts for top central beneficiaries
    for candidate in central_candidates[:3]:
        alert = await _create_alert(
            db, inv, candidate["account"],
            {
                "risk_score": min(candidate["composite_score"], 100),
                "severity": "HIGH" if candidate["composite_score"] >= 60 else "MEDIUM",
                "evidence": candidate["evidence"],
            },
            title=f"Potential central beneficiary: {candidate['account']}",
            alert_type="CENTRAL_BENEFICIARY_CANDIDATE",
        )
        alerts_created.append(alert)

    inv.status = InvestigationStatus.IN_PROGRESS
    inv.summary = json.dumps({
        "suspicious_nodes": len(suspicious_nodes),
        "fan_out_accounts": len(fan_out_list),
        "fan_in_accounts": len(fan_in_list),
        "cycles": len(cycles),
        "convergence_events": len(convergence_events),
        "central_candidates": len(central_candidates),
        "alerts_created": len(alerts_created),
    })

    await _log_audit(db, "INVESTIGATION_RUN", "investigation", investigation_id,
                     f"Investigation run complete. {len(alerts_created)} alerts created.")

    return {
        "investigation_id": investigation_id,
        "suspicious_nodes": list(suspicious_nodes),
        "forward_nodes": forward_result["nodes"],
        "backward_nodes": [n for r in backward_results for n in r["nodes"]],
        "fan_out": fan_out_list,
        "fan_in": fan_in_list,
        "cycles": cycles[:10],
        "convergence_events": convergence_events[:10],
        "central_candidates": central_candidates[:5],
        "alerts_created": len(alerts_created),
        "graph": cyto_data,
    }


async def expand_investigation(
    db: AsyncSession,
    investigation_id: str,
    account_ref: str,
    direction: str = "both",
    max_depth: int = 2,
) -> dict:
    """Expand an existing investigation from a specific node."""
    result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found")

    time_lo = datetime.now(timezone.utc) - timedelta(days=inv.time_window_days or 60)
    query = select(Transaction).where(Transaction.timestamp_utc >= time_lo)
    if inv.scenario_run_id:
        query = query.where(Transaction.scenario_run_id == inv.scenario_run_id)
    txn_result = await db.execute(query)
    all_txns = txn_result.scalars().all()

    G = build_graph([_txn_to_dict(t) for t in all_txns])

    expansion = {"account": account_ref, "direction": direction}
    if direction in ("forward", "both"):
        expansion["forward"] = forward_trace(G, account_ref, max_depth=max_depth)
    if direction in ("backward", "both"):
        expansion["backward"] = backward_trace(G, account_ref, max_depth=max_depth)

    await _log_audit(db, "INVESTIGATION_EXPANDED", "investigation", investigation_id,
                     f"Expanded from {account_ref}, direction={direction}")
    return expansion


async def get_investigation_timeline(
    db: AsyncSession, investigation_id: str
) -> list[dict]:
    """Return all relevant transactions in chronological order."""
    result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        return []

    query = select(Transaction).order_by(Transaction.timestamp_utc)
    if inv.scenario_run_id:
        query = query.where(Transaction.scenario_run_id == inv.scenario_run_id)
    txn_result = await db.execute(query)
    txns = txn_result.scalars().all()

    return [_txn_to_dict(t) for t in txns]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _txn_to_dict(t: Transaction) -> dict:
    return {
        "id": t.id,
        "transaction_ref": t.transaction_ref,
        "bank_id": t.bank_id,
        "source_bank_id": t.source_bank_id,
        "destination_bank_id": t.destination_bank_id,
        "sender_account_id": t.sender_account_id,
        "receiver_account_id": t.receiver_account_id,
        "sender_account_ref": t.sender_account_ref,
        "receiver_account_ref": t.receiver_account_ref,
        "amount": float(t.amount),
        "currency": t.currency,
        "timestamp_utc": t.timestamp_utc.isoformat() if t.timestamp_utc else None,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "is_suspicious": t.is_suspicious,
        "risk_score": float(t.risk_score or 0),
        "provenance_id": t.provenance_id,
        "scenario_run_id": t.scenario_run_id,
    }


async def _create_alert(
    db: AsyncSession,
    inv: Investigation,
    account_ref: str,
    risk_result: dict,
    title: str,
    alert_type: str,
) -> RiskAlert:
    # Find account ID by ref
    acc_result = await db.execute(
        select(Account).where(Account.account_ref == account_ref).limit(1)
    )
    acc = acc_result.scalar_one_or_none()

    severity_str = risk_result.get("severity", "MEDIUM")
    severity = AlertSeverity(severity_str) if severity_str in [e.value for e in AlertSeverity] else AlertSeverity.MEDIUM

    alert = RiskAlert(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        triggering_transaction_id=inv.starting_transaction_id,
        relevant_account_id=acc.id if acc else None,
        alert_type=alert_type,
        severity=severity,
        status=AlertStatus.OPEN,
        risk_score=float(risk_result.get("risk_score", 0)),
        title=title,
        evidence=json.dumps(risk_result.get("evidence", [])),
    )
    db.add(alert)
    await db.flush()
    return alert


async def _log_audit(
    db: AsyncSession, event_type: str, entity_type: str,
    entity_id: str, description: str,
):
    audit = AuditEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(audit)
    await db.flush()
