"""
Bank B Adapter — Native schema:
  reference, debit_acct, credit_acct, txn_amount (INR), txn_date (YYYY-MM-DD HH:MM:SS +05:30), txn_status
"""
from __future__ import annotations
import json
import uuid
from decimal import Decimal
from typing import Any
from app.adapters.base import BankAdapter, CanonicalTransaction, NormalisationResult


class BankBAdapter(BankAdapter):
    bank_code = "BANK_B"
    schema_version = "B_v2.1"

    VALID_STATUSES = {
        "SETTLED": "COMPLETED",
        "COMPLETED": "COMPLETED",
        "PROCESSING": "PENDING",
        "PENDING": "PENDING",
        "DECLINED": "FAILED",
        "FAILED": "FAILED",
        "RECALL": "REVERSED",
    }

    def __init__(self, bank_id: str):
        self.bank_id = bank_id
        self.adapter_used = "BankBAdapter_v2.1"

    def normalise(self, native_record: dict[str, Any]) -> NormalisationResult:
        raw = json.dumps(native_record)
        errors = []
        warnings = []

        reference = native_record.get("reference")
        debit_acct = native_record.get("debit_acct")
        credit_acct = native_record.get("credit_acct")
        txn_amount_raw = native_record.get("txn_amount")
        txn_date_raw = native_record.get("txn_date")
        status_raw = native_record.get("txn_status", "SETTLED")

        if not reference:
            errors.append("Missing required field: reference")
        if not debit_acct:
            errors.append("Missing required field: debit_acct")
        if not credit_acct:
            errors.append("Missing required field: credit_acct")
        if txn_amount_raw is None:
            errors.append("Missing required field: txn_amount")
        if not txn_date_raw:
            errors.append("Missing required field: txn_date")

        amount = self._to_decimal(txn_amount_raw)
        if amount is None:
            errors.append(f"Invalid txn_amount: {txn_amount_raw}")
        elif amount < Decimal("0"):
            errors.append("txn_amount must not be negative")

        # Bank B stores timestamps with IST offset (+05:30)
        timestamp = self._to_utc(txn_date_raw, tz_offset_hours=5.5)
        if timestamp is None:
            errors.append(f"Cannot parse txn_date: {txn_date_raw}")

        if errors:
            return NormalisationResult(
                status="REJECTED", errors=errors, warnings=warnings,
                source_reference=str(reference or ""), raw_payload=raw
            )

        canonical = CanonicalTransaction(
            transaction_id=str(uuid.uuid4()),
            bank_id=self.bank_id,
            sender_account_ref=str(debit_acct),
            receiver_account_ref=str(credit_acct),
            amount=amount,
            currency="INR",
            timestamp_utc=timestamp,
            status=self._map_status(status_raw),
            source_reference=str(reference),
            schema_version=self.schema_version,
            adapter_used=self.adapter_used,
            raw_payload=raw,
        )
        status = "WARNING" if warnings else "ACCEPTED"
        return NormalisationResult(
            status=status, canonical=canonical, errors=errors,
            warnings=warnings, source_reference=str(reference), raw_payload=raw
        )
