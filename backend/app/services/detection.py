"""
Behavioural Detection Engine.

Computes explainable behavioural features for accounts and transactions:
- Dwell time
- Pass-through ratio
- Transaction velocity
- Counterparty count
- Amount deviation from baseline
- Fan-out / fan-in
- Temporal convergence risk
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Feature computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_dwell_time(
    incoming_txns: list[dict],
    outgoing_txns: list[dict],
    relevant_in_refs: set[str] | None = None,
) -> dict:
    """
    Dwell time: time between relevant incoming and next outgoing transfer.
    Uses the earliest relevant incoming timestamp as the reference point.
    """
    if not incoming_txns or not outgoing_txns:
        return {"dwell_time_hours": None, "evidence": "Insufficient transactions to compute dwell time."}

    relevant_in = [t for t in incoming_txns if not relevant_in_refs or t.get("id") in relevant_in_refs]
    if not relevant_in:
        relevant_in = incoming_txns

    in_timestamps = [_parse_ts(t.get("timestamp_utc")) for t in relevant_in]
    in_timestamps = [t for t in in_timestamps if t]
    if not in_timestamps:
        return {"dwell_time_hours": None, "evidence": "Cannot parse incoming timestamps."}

    earliest_in = min(in_timestamps)
    out_timestamps = [_parse_ts(t.get("timestamp_utc")) for t in outgoing_txns]
    out_timestamps = [t for t in out_timestamps if t and t >= earliest_in]

    if not out_timestamps:
        return {"dwell_time_hours": None, "evidence": "No outgoing transfers after the relevant incoming transfer."}

    earliest_out = min(out_timestamps)
    dwell_seconds = (earliest_out - earliest_in).total_seconds()
    dwell_hours = dwell_seconds / 3600

    evidence = (
        f"Earliest relevant incoming: {earliest_in.isoformat()}. "
        f"Earliest subsequent outgoing: {earliest_out.isoformat()}. "
        f"Dwell time: {dwell_hours:.2f} hours."
    )
    return {"dwell_time_hours": round(dwell_hours, 4), "evidence": evidence}


def compute_pass_through_ratio(
    incoming_txns: list[dict],
    outgoing_txns: list[dict],
    relevant_in_ids: set[str] | None = None,
    relevant_out_ids: set[str] | None = None,
) -> dict:
    """
    Pass-through ratio = attributed outgoing ÷ relevant incoming × 100.
    Only compares amounts from the same relevant activity window.
    """
    relevant_in = [t for t in incoming_txns if not relevant_in_ids or t.get("id") in relevant_in_ids]
    relevant_out = [t for t in outgoing_txns if not relevant_out_ids or t.get("id") in relevant_out_ids]

    total_in = sum(Decimal(str(t.get("amount", 0))) for t in relevant_in)
    total_out = sum(Decimal(str(t.get("amount", 0))) for t in relevant_out)

    if total_in == 0:
        return {
            "pass_through_ratio": None,
            "total_relevant_in": 0,
            "total_relevant_out": float(total_out),
            "evidence": "No relevant incoming value to calculate pass-through ratio.",
        }

    ratio = (total_out / total_in * 100).quantize(Decimal("0.01"))
    evidence = (
        f"Relevant incoming: ₹{total_in:,.2f}. "
        f"Relevant outgoing: ₹{total_out:,.2f}. "
        f"Pass-through ratio: {ratio}%."
    )
    return {
        "pass_through_ratio": float(ratio),
        "total_relevant_in": float(total_in),
        "total_relevant_out": float(total_out),
        "evidence": evidence,
    }


def compute_velocity(
    transactions: list[dict],
    window_hours: float = 24.0,
    reference_ts: datetime | None = None,
) -> dict:
    """
    Transaction velocity within a time window around the reference timestamp.
    """
    ref = reference_ts or datetime.now(timezone.utc)
    lo = ref - timedelta(hours=window_hours / 2)
    hi = ref + timedelta(hours=window_hours / 2)

    window_txns = []
    for t in transactions:
        ts = _parse_ts(t.get("timestamp_utc"))
        if ts and lo <= ts <= hi:
            window_txns.append(t)

    count = len(window_txns)
    total_value = sum(Decimal(str(t.get("amount", 0))) for t in window_txns)

    return {
        "count_in_window": count,
        "value_in_window": float(total_value),
        "window_hours": window_hours,
        "evidence": (
            f"{count} transactions totalling ₹{total_value:,.2f} "
            f"within {window_hours}h window around {ref.isoformat()}."
        ),
    }


def compute_counterparty_count(
    transactions: list[dict],
    account_ref: str,
    window_days: int = 30,
    reference_ts: datetime | None = None,
) -> dict:
    """Count distinct counterparties within the relevant time window."""
    ref = reference_ts or datetime.now(timezone.utc)
    lo = ref - timedelta(days=window_days)
    counterparties = set()

    for t in transactions:
        ts = _parse_ts(t.get("timestamp_utc"))
        if not ts or ts < lo:
            continue
        sender = t.get("sender_account_ref", "")
        receiver = t.get("receiver_account_ref", "")
        if sender != account_ref:
            counterparties.add(sender)
        if receiver != account_ref:
            counterparties.add(receiver)

    return {
        "distinct_counterparties": len(counterparties),
        "window_days": window_days,
        "evidence": (
            f"{len(counterparties)} distinct counterparties within the last {window_days} days."
        ),
    }


def compute_amount_deviation(
    transaction_amount: float,
    baseline_avg: float,
    baseline_max: float,
) -> dict:
    """Compare a transaction amount against the account's historical baseline."""
    if baseline_avg <= 0:
        return {
            "z_score": None,
            "times_over_avg": None,
            "times_over_max": None,
            "evidence": "No baseline available for this account.",
        }

    z_score = (transaction_amount - baseline_avg) / max(baseline_avg, 1)
    times_over_avg = transaction_amount / baseline_avg if baseline_avg > 0 else 0
    times_over_max = transaction_amount / baseline_max if baseline_max > 0 else 0

    return {
        "z_score": round(z_score, 4),
        "times_over_avg": round(times_over_avg, 2),
        "times_over_max": round(times_over_max, 2),
        "evidence": (
            f"Transaction ₹{transaction_amount:,.2f} is {times_over_avg:.1f}× average "
            f"and {times_over_max:.1f}× historical max for this account."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Risk fusion
# ─────────────────────────────────────────────────────────────────────────────

def fuse_risk(features: dict[str, Any], config: dict | None = None) -> dict:
    """
    Combine multiple behavioural signals into a composite risk score (0–100).
    Returns the score and a list of contributing evidence items.

    config keys (all optional, with defaults):
      high_dwell_threshold_hours, low_dwell_threshold_hours,
      high_pass_through_threshold, high_velocity_count,
      high_counterparty_count, high_z_score,
      high_value_threshold (INR)
    """
    config = config or {}
    ht_high_dwell = config.get("high_dwell_threshold_hours", 2.0)
    ht_low_dwell = config.get("low_dwell_threshold_hours", 0.25)
    ht_pass_through = config.get("high_pass_through_threshold", 80.0)
    ht_velocity = config.get("high_velocity_count", 5)
    ht_counterparty = config.get("high_counterparty_count", 8)
    ht_z_score = config.get("high_z_score", 3.0)
    ht_high_value = config.get("high_value_threshold", 1_000_000)

    score = 0.0
    evidence = []

    # Dwell time
    dwell = features.get("dwell_time_hours")
    if dwell is not None:
        if dwell < ht_low_dwell:
            score += 25
            evidence.append(f"Very low dwell time ({dwell:.2f}h < {ht_low_dwell}h threshold) suggests rapid pass-through.")
        elif dwell < ht_high_dwell:
            score += 15
            evidence.append(f"Low dwell time ({dwell:.2f}h < {ht_high_dwell}h threshold).")

    # Pass-through ratio
    ptr = features.get("pass_through_ratio")
    if ptr is not None:
        if ptr >= ht_pass_through:
            score += 25
            evidence.append(f"Pass-through ratio {ptr:.1f}% exceeds threshold ({ht_pass_through}%), indicating most incoming value was forwarded quickly.")
        elif ptr >= 50:
            score += 10
            evidence.append(f"Pass-through ratio {ptr:.1f}% is elevated.")

    # Velocity
    vel_count = features.get("count_in_window")
    if vel_count is not None and vel_count >= ht_velocity:
        score += 15
        evidence.append(f"High transaction velocity: {vel_count} transactions in window (threshold: {ht_velocity}).")

    # Counterparty count
    cp_count = features.get("distinct_counterparties")
    if cp_count is not None and cp_count >= ht_counterparty:
        score += 10
        evidence.append(f"High counterparty count: {cp_count} distinct counterparties.")

    # Amount deviation
    z = features.get("z_score")
    if z is not None and z >= ht_z_score:
        score += 15
        evidence.append(f"Transaction amount significantly deviates from baseline (z-score: {z:.2f}).")

    # Transaction amount over threshold
    txn_amount = features.get("transaction_amount")
    if txn_amount and txn_amount >= ht_high_value:
        score += 10
        evidence.append(f"Transaction ₹{txn_amount:,.2f} meets or exceeds high-value threshold ₹{ht_high_value:,.0f}.")

    # Graph signals
    if features.get("fan_out"):
        score += 15
        evidence.append("Fan-out pattern detected: account distributes to multiple recipients.")
    if features.get("fan_in"):
        score += 15
        evidence.append("Fan-in pattern detected: account receives from multiple sources.")
    if features.get("cycle_detected"):
        score += 10
        evidence.append("Cycle detected in transaction network.")
    if features.get("temporal_convergence"):
        score += 10
        evidence.append("Temporal convergence: multiple suspicious paths reach this account within a short window.")

    score = min(score, 100.0)

    severity = "LOW"
    if score >= 75:
        severity = "CRITICAL"
    elif score >= 55:
        severity = "HIGH"
    elif score >= 35:
        severity = "MEDIUM"

    return {
        "risk_score": round(score, 2),
        "severity": severity,
        "evidence": evidence,
        "features_used": list(features.keys()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_ts(ts: Any) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    if isinstance(ts, str):
        try:
            from dateutil import parser
            dt = parser.parse(ts)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None
