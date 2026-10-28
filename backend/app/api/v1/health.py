"""Health and system status endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get("/system/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    from app.services.monitoring import monitoring_engine
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    monitoring_status = monitoring_engine.get_status() if monitoring_engine else {"status": "NOT_INITIALISED"}

    return {
        "application": "Mule Matrix",
        "version": "1.0.0",
        "environment": settings.app_env,
        "database_connected": db_ok,
        "high_value_threshold_inr": settings.high_value_threshold,
        "monitoring": monitoring_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "This is a prototype investigation platform. "
            "It does not connect to real banks, issue real CBDC, freeze real accounts, "
            "or constitute legal evidence of fraud."
        ),
    }
