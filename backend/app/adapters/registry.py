"""Adapter registry — maps bank_code to adapter instance."""
from app.adapters.bank_a import BankAAdapter
from app.adapters.bank_b import BankBAdapter
from app.adapters.bank_c import BankCAdapter
from app.adapters.bank_d import BankDAdapter
from app.adapters.base import BankAdapter

_REGISTRY: dict[str, type] = {
    "BANK_A": BankAAdapter,
    "BANK_B": BankBAdapter,
    "BANK_C": BankCAdapter,
    "BANK_D": BankDAdapter,
}


def get_adapter(bank_code: str, bank_id: str) -> BankAdapter:
    """Return an instantiated adapter for the given bank code."""
    cls = _REGISTRY.get(bank_code.upper())
    if cls is None:
        raise ValueError(f"No adapter registered for bank code: {bank_code}")
    return cls(bank_id=bank_id)


def list_adapters() -> list[dict]:
    return [
        {
            "bank_code": code,
            "adapter_class": cls.__name__,
            "schema_version": cls.schema_version,
        }
        for code, cls in _REGISTRY.items()
    ]
