"""Normalisation status and control endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models import NormalisationRecord, Bank
import json

router = APIRouter()


@router.get("/status")
async def normalisation_status(db: AsyncSession = Depends(get_db)):
    banks_result = await db.execute(select(Bank))
    banks = banks_result.scalars().all()
    bank_stats = []
    for bank in banks:
        stats = await db.execute(
            select(
                NormalisationRecord.status,
                func.count().label("count")
            ).where(NormalisationRecord.bank_id == bank.id)
            .group_by(NormalisationRecord.status)
        )
        status_counts = {row.status: row.count for row in stats}
        bank_stats.append({
            "bank_id": bank.id,
            "bank_code": bank.bank_code,
            "display_name": bank.display_name,
            "schema_version": bank.native_schema_version,
            "accepted": status_counts.get("ACCEPTED", 0),
            "rejected": status_counts.get("REJECTED", 0),
            "duplicate": status_counts.get("DUPLICATE", 0),
            "warning": status_counts.get("WARNING", 0),
            "total": sum(status_counts.values()),
        })
    return {"banks": bank_stats}


@router.get("/errors")
async def normalisation_errors(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    bank_id: str | None = None,
):
    query = select(NormalisationRecord).where(
        NormalisationRecord.status.in_(["REJECTED", "WARNING"])
    ).order_by(NormalisationRecord.created_at.desc())
    if bank_id:
        query = query.where(NormalisationRecord.bank_id == bank_id)
    result = await db.execute(query.limit(limit))
    records = result.scalars().all()
    return {
        "errors": [
            {
                "id": r.id,
                "bank_id": r.bank_id,
                "source_reference": r.source_reference,
                "status": r.status,
                "errors": json.loads(r.errors) if r.errors else [],
                "warnings": json.loads(r.warnings) if r.warnings else [],
                "adapter_used": r.adapter_used,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


@router.post("/run")
async def run_normalisation(db: AsyncSession = Depends(get_db)):
    """Trigger re-normalisation of any pending raw payloads (placeholder — adapters run on ingest)."""
    return {"status": "ok", "message": "Normalisation runs automatically on transaction ingestion."}
