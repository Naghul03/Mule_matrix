"""
Bank A Adapter — Native schema:
  txn_id, sender, receiver, amount (INR), timestamp (ISO 8601 UTC), status
"""
from __future__ import annotations
import json
import uuid
from decimal import Decimal
from typing import Any
from app.adapters.base import BankAdapter, CanonicalTransaction, NormalisationResult


class BankAAdapter(BankAdapter):
    bank_code = "BANK_A"
    schema_version = "A_v1.0"

    VALID_STATUSES = {
        "SUCCESS": "COMPLETED",
        "COMPLETED": "COMPLETED",
        "PENDING": "PENDING",
        "FAILED": "FAILED",
        "REVERSED": "REVERSED",
        "FLAGGED": "FLAGGED",
    }

    def __init__(self, bank_id: str):
        self.bank_id = bank_id
        self.adapter_used = "BankAAdapter_v1.0"

    def normalise(self, native_record: dict[str, Any]) -> NormalisationResult:
        raw = json.dumps(native_record)
        errors = []
        warnings = []

        txn_id = native_record.get("txn_id")
        sender = native_record.get("sender")
        receiver = native_record.get("receiver")
        amount_raw = native_record.get("amount")
        timestamp_raw = native_record.get("timestamp")
        status_raw = native_record.get("status", "SUCCESS")

        # Validation
        if not txn_id:
            errors.append("Missing required field: txn_id")
        if not sender:
            errors.append("Missing required field: sender")
        if not receiver:
            errors.append("Missing required field: receiver")
        if amount_raw is None:
            errors.append("Missing required field: amount")
        if not timestamp_raw:
            errors.append("Missing required field: timestamp")

        amount = self._to_decimal(amount_raw)
        if amount is None:
            errors.append(f"Invalid amount value: {amount_raw}")
        elif amount < Decimal("0"):
            errors.append("Amount must not be negative")
        elif amount == Decimal("0"):
            warnings.append("Zero-value transaction")

        timestamp = self._to_utc(timestamp_raw)
        if timestamp is None:
            errors.append(f"Cannot parse timestamp: {timestamp_raw}")

        if errors:
            return NormalisationResult(
                status="REJECTED", errors=errors, warnings=warnings,
                source_reference=str(txn_id or ""), raw_payload=raw
            )

        canonical = CanonicalTransaction(
            transaction_id=str(uuid.uuid4()),
            bank_id=self.bank_id,
            sender_account_ref=str(sender),
            receiver_account_ref=str(receiver),
            amount=amount,
            currency="INR",
            timestamp_utc=timestamp,
            status=self._map_status(status_raw),
            source_reference=str(txn_id),
            schema_version=self.schema_version,
            adapter_used=self.adapter_used,
            raw_payload=raw,
        )
        status = "WARNING" if warnings else "ACCEPTED"
        return NormalisationResult(
            status=status, canonical=canonical, errors=errors,
            warnings=warnings, source_reference=str(txn_id), raw_payload=raw
        )
