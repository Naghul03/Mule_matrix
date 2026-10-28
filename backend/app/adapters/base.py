"""Bank adapter base class and canonical transaction schema."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import json


@dataclass
class CanonicalTransaction:
    """Canonical transaction after normalisation from any bank adapter."""
    transaction_id: str
    bank_id: str
    sender_account_ref: str
    receiver_account_ref: str
    amount: Decimal
    currency: str
    timestamp_utc: datetime
    status: str
    source_reference: str
    schema_version: str
    adapter_used: str
    raw_payload: str = ""


@dataclass
class NormalisationResult:
    """Result of normalising a single native record."""
    status: str  # ACCEPTED, REJECTED, DUPLICATE, WARNING
    canonical: CanonicalTransaction | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_reference: str = ""
    raw_payload: str = ""


class BankAdapter(ABC):
    """Base class for all bank-specific normalisation adapters."""

    bank_id: str
    bank_code: str
    schema_version: str
    VALID_STATUSES: dict[str, str] = {}  # native_status -> canonical_status

    @abstractmethod
    def normalise(self, native_record: dict[str, Any]) -> NormalisationResult:
        """Normalise one native bank record to canonical form."""
        ...

    def normalise_batch(self, records: list[dict[str, Any]]) -> list[NormalisationResult]:
        """Normalise a list of native bank records."""
        return [self.normalise(r) for r in records]

    def _to_utc(self, ts: Any, fmt: str | None = None, tz_offset_hours: int = 0) -> datetime | None:
        """Parse a timestamp value into a UTC-aware datetime."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(timezone.utc)
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(ts, str):
            ts = ts.strip()
            try:
                from dateutil import parser as dateutil_parser
                dt = dateutil_parser.parse(ts)
                if dt.tzinfo is None:
                    from datetime import timedelta
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=tz_offset_hours)))
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
            for fmt_try in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y %H:%M:%S",
            ]:
                try:
                    dt = datetime.strptime(ts, fmt_try)
                    from datetime import timedelta
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=tz_offset_hours)))
                    return dt.astimezone(timezone.utc)
                except ValueError:
                    pass
        return None

    def _to_decimal(self, value: Any, unit_divisor: int = 1) -> Decimal | None:
        """Convert a value to Decimal, optionally dividing by a unit (e.g. paise→rupees)."""
        try:
            d = Decimal(str(value))
            if unit_divisor != 1:
                d = d / Decimal(unit_divisor)
            return d
        except Exception:
            return None

    def _map_status(self, native_status: str) -> str:
        return self.VALID_STATUSES.get(str(native_status).upper(), "COMPLETED")
