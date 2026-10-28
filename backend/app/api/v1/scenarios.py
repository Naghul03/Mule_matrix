"""Scenario endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import ScenarioRun
from app.services.scenario import SCENARIO_META, run_scenario, reset_scenario_run
import uuid

router = APIRouter()


@router.get("")
async def list_scenarios():
    return {
        "scenarios": [
            {
                "id": sid,
                "name": meta["name"],
                "description": meta["description"],
            }
            for sid, meta in SCENARIO_META.items()
        ]
    }


@router.post("/{scenario_id}/run")
async def execute_scenario(
    scenario_id: str,
    params: dict | None = None,
    db: AsyncSession = Depends(get_db),
):
    params = params or {}
    seed = params.get("seed", 42)
    timespan_days = params.get("timespan_days", 30)
    try:
        result = await run_scenario(db, scenario_id, seed=seed, timespan_days=timespan_days)
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/runs")
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScenarioRun).order_by(ScenarioRun.started_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return {"runs": [_run_out(r) for r in runs]}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScenarioRun).where(ScenarioRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_out(run)


@router.post("/runs/{run_id}/reset")
async def reset_run(run_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await reset_scenario_run(db, run_id)
        await db.commit()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _run_out(r: ScenarioRun) -> dict:
    return {
        "id": r.id,
        "scenario_id": r.scenario_id,
        "scenario_name": r.scenario_name,
        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        "seed": r.seed,
        "transactions_created": r.transactions_created,
        "accounts_created": r.accounts_created,
        "alerts_generated": r.alerts_generated,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }
