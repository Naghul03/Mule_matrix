"""API v1 package — aggregates all routers."""
from fastapi import APIRouter
from app.api.v1 import (
    health, banks, transactions, normalisation,
    scenarios, monitoring, investigations, provenance,
    alerts, dashboard,
)

router = APIRouter()
router.include_router(health.router, tags=["Health"])
router.include_router(banks.router, prefix="/banks", tags=["Banks"])
router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
router.include_router(normalisation.router, prefix="/normalisation", tags=["Normalisation"])
router.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
router.include_router(investigations.router, prefix="/investigations", tags=["Investigations"])
router.include_router(provenance.router, prefix="/provenance", tags=["Provenance"])
router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
