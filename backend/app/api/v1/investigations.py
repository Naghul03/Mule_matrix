"""Investigation endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import Investigation, RiskAlert
from app.services.investigation import (
    create_investigation, run_investigation,
    expand_investigation, get_investigation_timeline,
)
import json

router = APIRouter()


@router.get("")
async def list_investigations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Investigation).order_by(Investigation.created_at.desc()).limit(100)
    )
    invs = result.scalars().all()
    return {"investigations": [_inv_out(i) for i in invs]}


@router.post("")
async def create_new_investigation(payload: dict, db: AsyncSession = Depends(get_db)):
    try:
        inv = await create_investigation(
            db,
            entry_type=payload.get("entry_type", "AUTOMATIC"),
            starting_transaction_id=payload.get("starting_transaction_id"),
            starting_account_id=payload.get("starting_account_id"),
            scenario_run_id=payload.get("scenario_run_id"),
            scenario_id=payload.get("scenario_id"),
            title=payload.get("title"),
        )
        await db.commit()
        return _inv_out(inv)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return _inv_out(inv)


@router.get("/{investigation_id}/graph")
async def get_investigation_graph(investigation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    graph_data = json.loads(inv.graph_data) if inv.graph_data else {"elements": []}

    # Load alerts for this investigation
    alert_result = await db.execute(
        select(RiskAlert).where(RiskAlert.investigation_id == investigation_id)
    )
    alerts = alert_result.scalars().all()
    alert_list = [
        {
            "id": a.id,
            "account_ref": a.relevant_account_id,
            "title": a.title,
            "severity": a.severity.value,
            "risk_score": float(a.risk_score),
            "evidence": json.loads(a.evidence) if a.evidence else [],
        }
        for a in alerts
    ]

    return {
        "investigation_id": investigation_id,
        "graph": graph_data,
        "alerts": alert_list,
    }


@router.post("/{investigation_id}/expand")
async def expand_graph(
    investigation_id: str, payload: dict, db: AsyncSession = Depends(get_db)
):
    account_ref = payload.get("account_ref")
    direction = payload.get("direction", "both")
    max_depth = payload.get("max_depth", 2)
    if not account_ref:
        raise HTTPException(status_code=400, detail="account_ref required")
    try:
        result = await expand_investigation(db, investigation_id, account_ref, direction, max_depth)
        await db.commit()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{investigation_id}/timeline")
async def get_timeline(investigation_id: str, db: AsyncSession = Depends(get_db)):
    timeline = await get_investigation_timeline(db, investigation_id)
    return {"investigation_id": investigation_id, "events": timeline}


def _inv_out(i: Investigation) -> dict:
    return {
        "id": i.id,
        "entry_type": i.entry_type.value if hasattr(i.entry_type, "value") else str(i.entry_type),
        "starting_transaction_id": i.starting_transaction_id,
        "starting_account_id": i.starting_account_id,
        "scenario_run_id": i.scenario_run_id,
        "scenario_id": i.scenario_id,
        "status": i.status.value if hasattr(i.status, "value") else str(i.status),
        "title": i.title,
        "summary": json.loads(i.summary) if i.summary else None,
        "max_depth_forward": i.max_depth_forward,
        "max_depth_backward": i.max_depth_backward,
        "time_window_days": i.time_window_days,
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }
