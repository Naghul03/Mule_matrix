"""
Bank D Adapter — Native schema (wire/SWIFT-inspired):
  msg_id, ordering_account, beneficiary_account, instructed_amount, instructed_currency,
  value_date (YYYYMMDD), charge_code, transaction_type, msg_status
"""
from __future__ import annotations
import json
import uuid
from decimal import Decimal
from typing import Any
from app.adapters.base import BankAdapter, CanonicalTransaction, NormalisationResult

_FOREX_RATES_TO_INR: dict[str, Decimal] = {
    "INR": Decimal("1"),
    "USD": Decimal("83.5"),
    "EUR": Decimal("89.2"),
    "GBP": Decimal("104.1"),
    "AED": Decimal("22.7"),
}


class BankDAdapter(BankAdapter):
    bank_code = "BANK_D"
    schema_version = "D_v3.0"

    VALID_STATUSES = {
        "ACCP": "COMPLETED",   # AcceptedCustomerProfile
        "ACSC": "COMPLETED",   # AcceptedSettlementCompleted
        "ACSP": "PENDING",     # AcceptedSettlementInProcess
        "PDNG": "PENDING",     # Pending
        "RJCT": "FAILED",      # Rejected
        "CANC": "REVERSED",    # Cancelled
        "ACWC": "COMPLETED",   # AcceptedWithChange
    }

    def __init__(self, bank_id: str):
        self.bank_id = bank_id
        self.adapter_used = "BankDAdapter_v3.0"

    def normalise(self, native_record: dict[str, Any]) -> NormalisationResult:
        raw = json.dumps(native_record)
        errors = []
        warnings = []

        msg_id = native_record.get("msg_id")
        ordering_account = native_record.get("ordering_account")
        beneficiary_account = native_record.get("beneficiary_account")
        instructed_amount_raw = native_record.get("instructed_amount")
        instructed_currency = str(native_record.get("instructed_currency", "INR")).upper()
        value_date_raw = native_record.get("value_date")
        msg_status_raw = native_record.get("msg_status", "ACSC")
        transaction_type = native_record.get("transaction_type", "TRANSFER")

        if not msg_id:
            errors.append("Missing required field: msg_id")
        if not ordering_account:
            errors.append("Missing required field: ordering_account")
        if not beneficiary_account:
            errors.append("Missing required field: beneficiary_account")
        if instructed_amount_raw is None:
            errors.append("Missing required field: instructed_amount")
        if not value_date_raw:
            errors.append("Missing required field: value_date")

        # Currency conversion
        amount_in_original = self._to_decimal(instructed_amount_raw)
        amount_in_inr = None
        if amount_in_original is not None:
            if amount_in_original < Decimal("0"):
                errors.append("instructed_amount must not be negative")
            else:
                rate = _FOREX_RATES_TO_INR.get(instructed_currency)
                if rate is None:
                    warnings.append(f"Unknown currency {instructed_currency}; stored as-is")
                    amount_in_inr = amount_in_original
                    instructed_currency = instructed_currency
                else:
                    amount_in_inr = amount_in_original * rate
                    if instructed_currency != "INR":
                        warnings.append(
                            f"Converted {amount_in_original} {instructed_currency} → "
                            f"{amount_in_inr} INR at simulated rate {rate}"
                        )
        else:
            errors.append(f"Invalid instructed_amount: {instructed_amount_raw}")

        # Bank D uses YYYYMMDD date strings; treat as UTC midnight
        timestamp = None
        if value_date_raw:
            import re
            if re.match(r"^\d{8}$", str(value_date_raw)):
                from datetime import datetime, timezone
                try:
                    timestamp = datetime.strptime(str(value_date_raw), "%Y%m%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    errors.append(f"Cannot parse value_date: {value_date_raw}")
            else:
                timestamp = self._to_utc(value_date_raw)
                if timestamp is None:
                    errors.append(f"Cannot parse value_date: {value_date_raw}")

        if errors:
            return NormalisationResult(
                status="REJECTED", errors=errors, warnings=warnings,
                source_reference=str(msg_id or ""), raw_payload=raw
            )

        canonical = CanonicalTransaction(
            transaction_id=str(uuid.uuid4()),
            bank_id=self.bank_id,
            sender_account_ref=str(ordering_account),
            receiver_account_ref=str(beneficiary_account),
            amount=amount_in_inr,
            currency="INR",  # always stored in INR after conversion
            timestamp_utc=timestamp,
            status=self._map_status(msg_status_raw),
            source_reference=str(msg_id),
            schema_version=self.schema_version,
            adapter_used=self.adapter_used,
            raw_payload=raw,
        )
        status = "WARNING" if warnings else "ACCEPTED"
        return NormalisationResult(
            status=status, canonical=canonical, errors=errors,
            warnings=warnings, source_reference=str(msg_id), raw_payload=raw
        )
