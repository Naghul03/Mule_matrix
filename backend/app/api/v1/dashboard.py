"""Dashboard aggregate endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.models import (
    Transaction, Account, Investigation, RiskAlert,
    ScenarioRun, Bank, AuditEvent, AlertStatus, AlertSeverity,
)
from datetime import datetime, timedelta, timezone
import json

router = APIRouter()


@router.get("/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    # Total transactions
    total_txns = (await db.execute(select(func.count()).select_from(Transaction))).scalar() or 0
    suspicious_txns = (await db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.is_suspicious == True)
    )).scalar() or 0

    # Investigations
    open_invs = (await db.execute(
        select(func.count()).select_from(Investigation).where(
            Investigation.status.in_(["OPEN", "IN_PROGRESS"])
        )
    )).scalar() or 0

    # Accounts under review (marked suspicious)
    accounts_review = (await db.execute(
        select(func.count()).select_from(Account).where(Account.is_suspicious == True)
    )).scalar() or 0

    # Open alerts
    open_alerts = (await db.execute(
        select(func.count()).select_from(RiskAlert).where(
            RiskAlert.status == AlertStatus.OPEN
        )
    )).scalar() or 0
    high_risk_alerts = (await db.execute(
        select(func.count()).select_from(RiskAlert).where(
            RiskAlert.severity.in_(["HIGH", "CRITICAL"]),
            RiskAlert.status == AlertStatus.OPEN,
        )
    )).scalar() or 0

    # Banks online
    banks_online = (await db.execute(
        select(func.count()).select_from(Bank).where(Bank.is_active == True)
    )).scalar() or 0

    # Latest scenario run
    latest_run_result = await db.execute(
        select(ScenarioRun).order_by(ScenarioRun.started_at.desc()).limit(1)
    )
    latest_run = latest_run_result.scalar_one_or_none()

    return {
        "transactions_screened": total_txns,
        "suspicious_transactions_flagged": suspicious_txns,
        "open_investigations": open_invs,
        "accounts_under_review": accounts_review,
        "potential_mule_network_clusters": 0,  # computed by graph engine on demand
        "high_risk_off_ramp_alerts": high_risk_alerts,
        "simulated_banks_online": banks_online,
        "open_alerts": open_alerts,
        "latest_scenario": {
            "id": latest_run.id if latest_run else None,
            "name": latest_run.scenario_name if latest_run else None,
            "status": latest_run.status.value if latest_run and hasattr(latest_run.status, "value") else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/activity")
async def recent_activity(db: AsyncSession = Depends(get_db)):
    """Recent alerts and investigation activity for the activity feed."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    alert_result = await db.execute(
        select(RiskAlert).where(RiskAlert.created_at >= cutoff)
        .order_by(RiskAlert.created_at.desc()).limit(20)
    )
    alerts = alert_result.scalars().all()

    audit_result = await db.execute(
        select(AuditEvent).where(AuditEvent.created_at >= cutoff)
        .order_by(AuditEvent.created_at.desc()).limit(20)
    )
    audits = audit_result.scalars().all()

    feed = []
    for a in alerts:
        feed.append({
            "type": "ALERT",
            "timestamp": a.created_at.isoformat() if a.created_at else None,
            "event_type": a.alert_type,
            "title": a.title,
            "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
            "investigation_id": a.investigation_id,
            "reference": a.id,
        })
    for ev in audits:
        feed.append({
            "type": "AUDIT",
            "timestamp": ev.created_at.isoformat() if ev.created_at else None,
            "event_type": ev.event_type,
            "title": ev.description or ev.event_type,
            "severity": None,
            "investigation_id": ev.entity_id if ev.entity_type == "investigation" else None,
            "reference": ev.id,
        })

    feed.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return {"activity": feed[:30]}


@router.get("/risk-distribution")
async def risk_distribution(db: AsyncSession = Depends(get_db)):
    """Alert distribution by severity and status."""
    result = await db.execute(
        select(RiskAlert.severity, func.count().label("count"))
        .group_by(RiskAlert.severity)
    )
    by_severity = [{"severity": row.severity, "count": row.count} for row in result]

    result2 = await db.execute(
        select(RiskAlert.status, func.count().label("count"))
        .group_by(RiskAlert.status)
    )
    by_status = [{"status": row.status, "count": row.count} for row in result2]

    # Transaction amounts over time (last 30 days, bucketed by day)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    txn_result = await db.execute(
        select(Transaction.timestamp_utc, Transaction.amount, Transaction.is_suspicious)
        .where(Transaction.timestamp_utc >= cutoff)
        .order_by(Transaction.timestamp_utc)
    )
    txns = txn_result.all()

    day_buckets: dict[str, dict] = {}
    for ts, amt, susp in txns:
        day = ts.strftime("%Y-%m-%d") if ts else "unknown"
        if day not in day_buckets:
            day_buckets[day] = {"date": day, "total": 0, "suspicious": 0, "count": 0}
        day_buckets[day]["total"] += float(amt)
        day_buckets[day]["count"] += 1
        if susp:
            day_buckets[day]["suspicious"] += float(amt)

    return {
        "by_severity": by_severity,
        "by_status": by_status,
        "daily_transactions": list(day_buckets.values()),
    }
