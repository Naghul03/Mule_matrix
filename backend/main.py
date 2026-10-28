"""Mule Matrix Backend — FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.models import base  # noqa: F401

app = FastAPI(
    title="Mule Matrix API",
    description="Financial Fraud Investigation Platform — Follow the Money. Uncover the Network.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialise database tables and monitoring engine on startup."""
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.services.monitoring import init_monitoring_engine
    init_monitoring_engine(AsyncSessionLocal)


@app.on_event("shutdown")
async def shutdown_event():
    from app.services.monitoring import monitoring_engine
    if monitoring_engine:
        monitoring_engine.stop()


@app.get("/")
async def root():
    return {"message": "Mule Matrix API", "version": "1.0.0", "docs": "/docs"}
