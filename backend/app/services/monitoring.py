"""
Automatic Monitoring Engine.

A lightweight asynchronous background task that:
1. Polls for new unprocessed transactions
2. Runs behavioural checks
3. Creates investigations and alerts where appropriate
4. Makes event processing idempotent
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    Transaction, Account, Investigation, RiskAlert, AuditEvent,
    AlertSeverity, AlertStatus, InvestigationStatus, InvestigationEntryType,
    TransactionStatus,
)
from app.services.detection import fuse_risk, compute_velocity, compute_counterparty_count
from app.services.graph_engine import build_graph, detect_fan_out, detect_fan_in
from app.core.config import settings


class MonitoringEngine:
    """Lightweight in-process monitoring loop."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self._running = False
        self._task: asyncio.Task | None = None
        self.processed_count = 0
        self.alerts_generated = 0
        self.last_run_at: datetime | None = None
        self.status = "STOPPED"

    def start(self):
        if self._running:
            return
        self._running = True
        self.status = "RUNNING"
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        self._running = False
        self.status = "STOPPED"
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self):
        while self._running:
            try:
                await self._process_batch()
                self.last_run_at = datetime.now(timezone.utc)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                # Log and continue — do not crash the loop
                print(f"[MonitoringEngine] Error in loop: {exc}")
            await asyncio.sleep(settings.monitoring_poll_interval_seconds)

    async def _process_batch(self):
        """Process recent unscreened transactions idempotently."""
        async with self.session_factory() as db:
            from sqlalchemy import select, update
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

            # Fetch unscreened transactions created recently
            result = await db.execute(
                select(Transaction).where(
                    Transaction.is_suspicious == False,
                    Transaction.created_at >= cutoff,
                ).order_by(Transaction.timestamp_utc).limit(50)
            )
            txns = result.scalars().all()
            if not txns:
                return

            # Build a local mini-graph for this batch
            txn_dicts = [self._txn_to_dict(t) for t in txns]
            G = build_graph(txn_dicts)
            fan_out = detect_fan_out(G, threshold=3)
            fan_in = detect_fan_in(G, threshold=3)
            fan_out_accounts = {r["account"] for r in fan_out}
            fan_in_accounts = {r["account"] for r in fan_in}

            for txn in txns:
                features = {
                    "transaction_amount": float(txn.amount),
                    "fan_out": txn.sender_account_ref in fan_out_accounts,
                    "fan_in": txn.receiver_account_ref in fan_in_accounts,
                }
                if float(txn.amount) >= settings.high_value_threshold:
                    features["above_threshold"] = True

                risk = fuse_risk(features, {
                    "high_value_threshold": settings.high_value_threshold,
                })

                if risk["risk_score"] >= 30:
                    txn.is_suspicious = True
                    txn.risk_score = risk["risk_score"]

                    # Idempotency: don't create a duplicate alert for the same txn
                    existing_alert = await db.execute(
                        select(RiskAlert).where(
                            RiskAlert.triggering_transaction_id == txn.id
                        ).limit(1)
                    )
                    if existing_alert.scalar_one_or_none() is None:
                        alert = RiskAlert(
                            id=str(uuid.uuid4()),
                            triggering_transaction_id=txn.id,
                            relevant_account_id=txn.sender_account_id,
                            alert_type="AUTOMATIC_MONITORING",
                            severity=AlertSeverity(risk["severity"]) if risk["severity"] in [e.value for e in AlertSeverity] else AlertSeverity.MEDIUM,
                            status=AlertStatus.OPEN,
                            risk_score=risk["risk_score"],
                            title=f"Suspicious transaction {txn.transaction_ref}",
                            evidence=json.dumps(risk["evidence"]),
                        )
                        db.add(alert)
                        self.alerts_generated += 1

                self.processed_count += 1

            await db.commit()

    def _txn_to_dict(self, t: Transaction) -> dict:
        return {
            "id": t.id,
            "transaction_ref": t.transaction_ref,
            "bank_id": t.bank_id,
            "source_bank_id": t.source_bank_id,
            "sender_account_ref": t.sender_account_ref,
            "receiver_account_ref": t.receiver_account_ref,
            "amount": float(t.amount),
            "currency": t.currency,
            "timestamp_utc": t.timestamp_utc.isoformat() if t.timestamp_utc else None,
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "is_suspicious": t.is_suspicious,
            "risk_score": float(t.risk_score or 0),
        }

    def get_status(self) -> dict:
        return {
            "status": self.status,
            "running": self._running,
            "processed_count": self.processed_count,
            "alerts_generated": self.alerts_generated,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "poll_interval_seconds": settings.monitoring_poll_interval_seconds,
        }


# Global singleton — initialised in main.py startup
monitoring_engine: MonitoringEngine | None = None


def get_monitoring_engine() -> MonitoringEngine:
    global monitoring_engine
    if monitoring_engine is None:
        raise RuntimeError("Monitoring engine not initialised")
    return monitoring_engine


def init_monitoring_engine(session_factory: async_sessionmaker):
    global monitoring_engine
    monitoring_engine = MonitoringEngine(session_factory)
