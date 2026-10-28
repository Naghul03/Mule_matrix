"""Banks endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models import Bank, Account, Transaction

router = APIRouter()


@router.get("")
async def list_banks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank).where(Bank.is_active == True))
    banks = result.scalars().all()
    out = []
    for bank in banks:
        acc_count = await db.execute(
            select(func.count()).select_from(Account).where(Account.bank_id == bank.id)
        )
        txn_count = await db.execute(
            select(func.count()).select_from(Transaction).where(Transaction.bank_id == bank.id)
        )
        out.append({
            "id": bank.id,
            "bank_code": bank.bank_code,
            "display_name": bank.display_name,
            "native_schema_version": bank.native_schema_version,
            "description": bank.description,
            "is_active": bank.is_active,
            "account_count": acc_count.scalar() or 0,
            "transaction_count": txn_count.scalar() or 0,
            "created_at": bank.created_at.isoformat() if bank.created_at else None,
        })
    return {"banks": out, "total": len(out)}
