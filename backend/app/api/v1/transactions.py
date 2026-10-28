"""Transactions endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models import Transaction, Account, Bank

router = APIRouter()


@router.get("")
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    bank_id: str | None = None,
    scenario_run_id: str | None = None,
    is_suspicious: bool | None = None,
):
    query = select(Transaction).order_by(Transaction.timestamp_utc.desc())
    if bank_id:
        query = query.where(Transaction.bank_id == bank_id)
    if scenario_run_id:
        query = query.where(Transaction.scenario_run_id == scenario_run_id)
    if is_suspicious is not None:
        query = query.where(Transaction.is_suspicious == is_suspicious)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query.offset(offset).limit(limit))
    txns = result.scalars().all()

    return {
        "transactions": [_txn_out(t) for t in txns],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{transaction_id}")
async def get_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _txn_out(txn)


@router.get("/{transaction_id}/lineage")
async def get_transaction_lineage(transaction_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    provenance = None
    if txn.provenance_id:
        from app.models import ProvenanceRecord
        prov_result = await db.execute(
            select(ProvenanceRecord).where(ProvenanceRecord.id == txn.provenance_id)
        )
        prov = prov_result.scalar_one_or_none()
        if prov:
            provenance = {
                "id": prov.id,
                "mode": prov.mode.value,
                "parent_id": prov.parent_id,
                "initial_amount": float(prov.initial_amount),
                "remaining_amount": float(prov.remaining_amount),
                "status": prov.status.value,
            }
    return {"transaction": _txn_out(txn), "provenance": provenance}


@router.post("/ingest")
async def ingest_transaction(payload: dict, db: AsyncSession = Depends(get_db)):
    """Ingest a single native bank transaction record through the normalisation pipeline."""
    from app.adapters.registry import get_adapter
    from app.models import NormalisationRecord, Bank
    import json, uuid

    bank_code = payload.get("bank_code")
    native_record = payload.get("native_record")
    if not bank_code or not native_record:
        raise HTTPException(status_code=400, detail="bank_code and native_record required")

    bank_result = await db.execute(select(Bank).where(Bank.bank_code == bank_code))
    bank = bank_result.scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail=f"Bank {bank_code} not found")

    adapter = get_adapter(bank_code, bank.id)
    norm = adapter.normalise(native_record)

    norm_rec = NormalisationRecord(
        id=str(uuid.uuid4()),
        bank_id=bank.id,
        source_reference=norm.source_reference,
        status=norm.status,
        schema_version=adapter.schema_version,
        adapter_used=adapter.adapter_used,
        errors=json.dumps(norm.errors),
        warnings=json.dumps(norm.warnings),
        raw_payload=(norm.raw_payload or "")[:2000],
    )

    txn_id = None
    if norm.canonical:
        can = norm.canonical
        txn = Transaction(
            id=str(uuid.uuid4()),
            transaction_ref=can.source_reference,
            source_reference=can.source_reference,
            bank_id=bank.id,
            source_bank_id=bank.id,
            sender_account_ref=can.sender_account_ref,
            receiver_account_ref=can.receiver_account_ref,
            amount=can.amount,
            currency=can.currency,
            timestamp_utc=can.timestamp_utc,
            status="COMPLETED",
            schema_version=can.schema_version,
            adapter_used=can.adapter_used,
            raw_payload=(can.raw_payload or "")[:2000],
        )
        db.add(txn)
        await db.flush()
        norm_rec.canonical_transaction_id = txn.id
        txn_id = txn.id

    db.add(norm_rec)
    await db.commit()

    return {
        "status": norm.status,
        "transaction_id": txn_id,
        "errors": norm.errors,
        "warnings": norm.warnings,
    }


def _txn_out(t: Transaction) -> dict:
    return {
        "id": t.id,
        "transaction_ref": t.transaction_ref,
        "source_reference": t.source_reference,
        "bank_id": t.bank_id,
        "source_bank_id": t.source_bank_id,
        "destination_bank_id": t.destination_bank_id,
        "sender_account_id": t.sender_account_id,
        "receiver_account_id": t.receiver_account_id,
        "sender_account_ref": t.sender_account_ref,
        "receiver_account_ref": t.receiver_account_ref,
        "amount": float(t.amount),
        "currency": t.currency,
        "timestamp_utc": t.timestamp_utc.isoformat() if t.timestamp_utc else None,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "is_suspicious": t.is_suspicious,
        "risk_score": float(t.risk_score or 0),
        "schema_version": t.schema_version,
        "adapter_used": t.adapter_used,
        "provenance_id": t.provenance_id,
        "scenario_run_id": t.scenario_run_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
