"""Alerts and case management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models import RiskAlert, AlertStatus, AlertSeverity, AuditEvent
from datetime import datetime, timezone
import json, uuid

router = APIRouter()


@router.get("")
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(RiskAlert).order_by(RiskAlert.created_at.desc())
    if status:
        query = query.where(RiskAlert.status == status)
    if severity:
        query = query.where(RiskAlert.severity == severity)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.offset(offset).limit(limit))
    alerts = result.scalars().all()

    return {
        "alerts": [_alert_out(a) for a in alerts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{alert_id}")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RiskAlert).where(RiskAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_out(alert)


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Update alert status and add resolution notes."""
    result = await db.execute(select(RiskAlert).where(RiskAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    allowed_statuses = {s.value for s in AlertStatus}
    new_status = payload.get("status")
    if new_status and new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    if new_status:
        alert.status = AlertStatus(new_status)
        if new_status in ("CLOSED", "FALSE_POSITIVE"):
            alert.closed_at = datetime.now(timezone.utc)

    if "resolution_notes" in payload:
        alert.resolution_notes = payload["resolution_notes"]

    # Audit
    audit = AuditEvent(
        id=str(uuid.uuid4()),
        event_type="ALERT_UPDATED",
        entity_type="alert",
        entity_id=alert_id,
        description=f"Alert status → {new_status}. Notes: {payload.get('resolution_notes', '')}",
    )
    db.add(audit)
    await db.commit()
    return _alert_out(alert)


def _alert_out(a: RiskAlert) -> dict:
    return {
        "id": a.id,
        "investigation_id": a.investigation_id,
        "triggering_transaction_id": a.triggering_transaction_id,
        "relevant_account_id": a.relevant_account_id,
        "alert_type": a.alert_type,
        "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
        "status": a.status.value if hasattr(a.status, "value") else str(a.status),
        "risk_score": float(a.risk_score or 0),
        "title": a.title,
        "description": a.description,
        "evidence": json.loads(a.evidence) if a.evidence else [],
        "resolution_notes": a.resolution_notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        "closed_at": a.closed_at.isoformat() if a.closed_at else None,
    }
