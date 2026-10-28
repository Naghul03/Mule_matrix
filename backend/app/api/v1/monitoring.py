"""Monitoring control endpoints."""
from fastapi import APIRouter, HTTPException
from app.services.monitoring import get_monitoring_engine

router = APIRouter()


@router.get("/status")
async def monitoring_status():
    try:
        engine = get_monitoring_engine()
        return engine.get_status()
    except RuntimeError as exc:
        return {"status": "NOT_INITIALISED", "error": str(exc)}


@router.post("/start")
async def start_monitoring():
    try:
        engine = get_monitoring_engine()
        engine.start()
        return {"status": "started", "message": "Monitoring engine started"}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/stop")
async def stop_monitoring():
    try:
        engine = get_monitoring_engine()
        engine.stop()
        return {"status": "stopped", "message": "Monitoring engine stopped"}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
