"""Provenance endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import ProvenanceRecord

router = APIRouter()


@router.get("/{provenance_id}")
async def get_provenance(provenance_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProvenanceRecord).where(ProvenanceRecord.id == provenance_id)
    )
    prov = result.scalar_one_or_none()
    if not prov:
        raise HTTPException(status_code=404, detail="Provenance record not found")
    return _prov_out(prov)


@router.get("/{provenance_id}/tree")
async def get_provenance_tree(provenance_id: str, db: AsyncSession = Depends(get_db)):
    """Return the full lineage tree starting from provenance_id."""
    result = await db.execute(
        select(ProvenanceRecord).where(ProvenanceRecord.id == provenance_id)
    )
    root = result.scalar_one_or_none()
    if not root:
        raise HTTPException(status_code=404, detail="Provenance record not found")

    all_result = await db.execute(select(ProvenanceRecord))
    all_records = {r.id: r for r in all_result.scalars().all()}

    tree = _build_tree(root, all_records)
    return {"root_id": provenance_id, "tree": tree}


@router.get("")
async def list_provenance(
    db: AsyncSession = Depends(get_db),
    mode: str | None = None,
    investigation_id: str | None = None,
):
    query = select(ProvenanceRecord).order_by(ProvenanceRecord.created_at.desc()).limit(100)
    if mode:
        query = query.where(ProvenanceRecord.mode == mode)
    if investigation_id:
        query = query.where(ProvenanceRecord.investigation_id == investigation_id)
    result = await db.execute(query)
    records = result.scalars().all()
    return {"provenance_records": [_prov_out(r) for r in records]}


def _prov_out(p: ProvenanceRecord) -> dict:
    return {
        "id": p.id,
        "parent_id": p.parent_id,
        "mode": p.mode.value if hasattr(p.mode, "value") else str(p.mode),
        "origin_transaction_ref": p.origin_transaction_ref,
        "initial_amount": float(p.initial_amount),
        "attributed_amount": float(p.attributed_amount),
        "remaining_amount": float(p.remaining_amount),
        "currency": p.currency,
        "current_holder_account_id": p.current_holder_account_id,
        "allocation_method": p.allocation_method.value if hasattr(p.allocation_method, "value") else str(p.allocation_method),
        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
        "investigation_id": p.investigation_id,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _build_tree(node: ProvenanceRecord, all_records: dict) -> dict:
    children = [r for r in all_records.values() if r.parent_id == node.id]
    return {
        **_prov_out(node),
        "children": [_build_tree(c, all_records) for c in children],
    }
