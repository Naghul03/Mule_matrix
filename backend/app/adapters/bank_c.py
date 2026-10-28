"""
Bank C Adapter — Native schema:
  id, from_account, to_account, value_paise (integer paise), event_time (Unix epoch seconds), event_status
"""
from __future__ import annotations
import json
import uuid
from decimal import Decimal
from typing import Any
from app.adapters.base import BankAdapter, CanonicalTransaction, NormalisationResult

_PAISE_PER_RUPEE = 100


class BankCAdapter(BankAdapter):
    bank_code = "BANK_C"
    schema_version = "C_v1.5"

    VALID_STATUSES = {
        "CREDIT": "COMPLETED",
        "DEBIT": "COMPLETED",
        "SUCCESS": "COMPLETED",
        "COMPLETE": "COMPLETED",
        "INITIATED": "PENDING",
        "PENDING": "PENDING",
        "ERROR": "FAILED",
        "FAILED": "FAILED",
        "RETURNED": "REVERSED",
    }

    def __init__(self, bank_id: str):
        self.bank_id = bank_id
        self.adapter_used = "BankCAdapter_v1.5"

    def normalise(self, native_record: dict[str, Any]) -> NormalisationResult:
        raw = json.dumps(native_record)
        errors = []
        warnings = []

        record_id = native_record.get("id")
        from_account = native_record.get("from_account")
        to_account = native_record.get("to_account")
        value_paise_raw = native_record.get("value_paise")
        event_time_raw = native_record.get("event_time")
        status_raw = native_record.get("event_status", "SUCCESS")

        if not record_id:
            errors.append("Missing required field: id")
        if not from_account:
            errors.append("Missing required field: from_account")
        if not to_account:
            errors.append("Missing required field: to_account")
        if value_paise_raw is None:
            errors.append("Missing required field: value_paise")
        if event_time_raw is None:
            errors.append("Missing required field: event_time")

        # Bank C stores amounts in paise (integer); convert to rupees
        amount = None
        if value_paise_raw is not None:
            try:
                paise = int(value_paise_raw)
                if paise < 0:
                    errors.append("value_paise must not be negative")
                else:
                    amount = Decimal(paise) / Decimal(_PAISE_PER_RUPEE)
                    if amount == Decimal("0"):
                        warnings.append("Zero-value transaction (0 paise)")
            except (ValueError, TypeError):
                errors.append(f"Invalid value_paise: {value_paise_raw}")

        # Bank C uses Unix epoch seconds
        timestamp = self._to_utc(event_time_raw)
        if timestamp is None:
            errors.append(f"Cannot parse event_time: {event_time_raw}")

        if errors:
            return NormalisationResult(
                status="REJECTED", errors=errors, warnings=warnings,
                source_reference=str(record_id or ""), raw_payload=raw
            )

        canonical = CanonicalTransaction(
            transaction_id=str(uuid.uuid4()),
            bank_id=self.bank_id,
            sender_account_ref=str(from_account),
            receiver_account_ref=str(to_account),
            amount=amount,
            currency="INR",
            timestamp_utc=timestamp,
            status=self._map_status(status_raw),
            source_reference=str(record_id),
            schema_version=self.schema_version,
            adapter_used=self.adapter_used,
            raw_payload=raw,
        )
        status = "WARNING" if warnings else "ACCEPTED"
        return NormalisationResult(
            status=status, canonical=canonical, errors=errors,
            warnings=warnings, source_reference=str(record_id), raw_payload=raw
        )
