"""All SQLAlchemy ORM models for Mule Matrix."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    String, Text, DECIMAL, Boolean, Integer, ForeignKey,
    DateTime, Enum, Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    FLAGGED = "FLAGGED"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class InvestigationStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class InvestigationEntryType(str, enum.Enum):
    AUTOMATIC = "AUTOMATIC"
    REPORTED_FRAUD = "REPORTED_FRAUD"


class ProvenanceMode(str, enum.Enum):
    CONVENTIONAL = "CONVENTIONAL"
    CBDC_LINEAGE = "CBDC_LINEAGE"


class ProvenanceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    TRANSFERRED = "TRANSFERRED"
    SPLIT = "SPLIT"
    DEPLETED = "DEPLETED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"


class AllocationMethod(str, enum.Enum):
    FIFO = "FIFO"
    PROPORTIONAL = "PROPORTIONAL"


class ScenarioRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RESET = "RESET"


class OffRampStatus(str, enum.Enum):
    OBSERVED = "OBSERVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ESCALATED = "ESCALATED"
    SIMULATED_HOLD = "SIMULATED_HOLD"
    CLOSED = "CLOSED"


# ─────────────────────────────────────────────────────────────────────────────
# Banks
# ─────────────────────────────────────────────────────────────────────────────

class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    bank_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    native_schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="bank")
    transactions_sent: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.source_bank_id", back_populates="source_bank"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Accounts
# ─────────────────────────────────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("bank_id", "account_ref", name="uq_bank_account_ref"),
        Index("ix_accounts_bank_id", "bank_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    bank_id: Mapped[str] = mapped_column(String(36), ForeignKey("banks.id"), nullable=False)
    account_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), default="SAVINGS")
    owner_name: Mapped[str] = mapped_column(String(200), nullable=True)
    opening_balance: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), default=Decimal("0"))
    current_balance: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    simulated_device_id: Mapped[str] = mapped_column(String(100), nullable=True)
    simulated_ip: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    bank: Mapped["Bank"] = relationship("Bank", back_populates="accounts")
    baselines: Mapped[list["AccountBaseline"]] = relationship("AccountBaseline", back_populates="account")
    sent_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.sender_account_id", back_populates="sender_account"
    )
    received_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.receiver_account_id", back_populates="receiver_account"
    )


class AccountBaseline(Base):
    __tablename__ = "account_baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False)
    avg_transaction_amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), default=Decimal("0"))
    avg_monthly_volume: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), default=Decimal("0"))
    avg_counterparty_count: Mapped[int] = mapped_column(Integer, default=0)
    typical_transaction_hours: Mapped[str] = mapped_column(String(200), nullable=True)  # JSON string
    max_single_transaction: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), default=Decimal("0"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped["Account"] = relationship("Account", back_populates="baselines")


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_timestamp", "timestamp_utc"),
        Index("ix_transactions_sender", "sender_account_id"),
        Index("ix_transactions_receiver", "receiver_account_id"),
        Index("ix_transactions_source_bank", "source_bank_id"),
        Index("ix_transactions_scenario_run", "scenario_run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    transaction_ref: Mapped[str] = mapped_column(String(200), nullable=False)  # canonical txn ID
    source_reference: Mapped[str] = mapped_column(String(200), nullable=True)  # original bank ref
    bank_id: Mapped[str] = mapped_column(String(36), ForeignKey("banks.id"), nullable=False)
    source_bank_id: Mapped[str] = mapped_column(String(36), ForeignKey("banks.id"), nullable=True)
    destination_bank_id: Mapped[str] = mapped_column(String(36), ForeignKey("banks.id"), nullable=True)
    sender_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    receiver_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    sender_account_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    receiver_account_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.COMPLETED
    )
    schema_version: Mapped[str] = mapped_column(String(20), nullable=True)
    adapter_used: Mapped[str] = mapped_column(String(100), nullable=True)
    provenance_id: Mapped[str] = mapped_column(String(36), ForeignKey("provenance_records.id"), nullable=True)
    scenario_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenario_runs.id"), nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    simulated_device_id: Mapped[str] = mapped_column(String(100), nullable=True)
    simulated_ip: Mapped[str] = mapped_column(String(50), nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=True)  # original native record (JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source_bank: Mapped["Bank"] = relationship("Bank", foreign_keys=[source_bank_id], back_populates="transactions_sent")
    sender_account: Mapped["Account"] = relationship("Account", foreign_keys=[sender_account_id], back_populates="sent_transactions")
    receiver_account: Mapped["Account"] = relationship("Account", foreign_keys=[receiver_account_id], back_populates="received_transactions")
    provenance_record: Mapped["ProvenanceRecord"] = relationship("ProvenanceRecord", back_populates="transactions")


# ─────────────────────────────────────────────────────────────────────────────
# Provenance
# ─────────────────────────────────────────────────────────────────────────────

class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"
    __table_args__ = (
        Index("ix_provenance_investigation", "investigation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    parent_id: Mapped[str] = mapped_column(String(36), ForeignKey("provenance_records.id"), nullable=True)
    mode: Mapped[ProvenanceMode] = mapped_column(Enum(ProvenanceMode), default=ProvenanceMode.CONVENTIONAL)
    origin_transaction_ref: Mapped[str] = mapped_column(String(200), nullable=True)
    initial_amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), nullable=False)
    attributed_amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    current_holder_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    allocation_method: Mapped[AllocationMethod] = mapped_column(
        Enum(AllocationMethod), default=AllocationMethod.FIFO
    )
    status: Mapped[ProvenanceStatus] = mapped_column(
        Enum(ProvenanceStatus), default=ProvenanceStatus.ACTIVE
    )
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    parent: Mapped["ProvenanceRecord"] = relationship("ProvenanceRecord", remote_side="ProvenanceRecord.id", back_populates="children")
    children: Mapped[list["ProvenanceRecord"]] = relationship("ProvenanceRecord", back_populates="parent")
    movements: Mapped[list["ProvenanceMovement"]] = relationship("ProvenanceMovement", back_populates="provenance_record")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="provenance_record")
    current_holder: Mapped["Account"] = relationship("Account", foreign_keys=[current_holder_account_id])


class ProvenanceMovement(Base):
    __tablename__ = "provenance_movements"
    __table_args__ = (
        Index("ix_prov_movement_provenance", "provenance_record_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provenance_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("provenance_records.id"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True)
    from_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    to_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    attributed_amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), nullable=False)
    allocation_method: Mapped[str] = mapped_column(String(20), default="FIFO")
    fee_retained: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), default=Decimal("0"))
    movement_type: Mapped[str] = mapped_column(String(50), default="TRANSFER")  # TRANSFER, SPLIT, FEE, INITIAL
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    provenance_record: Mapped["ProvenanceRecord"] = relationship("ProvenanceRecord", back_populates="movements")
    transaction: Mapped["Transaction"] = relationship("Transaction", foreign_keys=[transaction_id])
    from_account: Mapped["Account"] = relationship("Account", foreign_keys=[from_account_id])
    to_account: Mapped["Account"] = relationship("Account", foreign_keys=[to_account_id])


# ─────────────────────────────────────────────────────────────────────────────
# Investigations
# ─────────────────────────────────────────────────────────────────────────────

class Investigation(Base):
    __tablename__ = "investigations"
    __table_args__ = (
        Index("ix_investigations_status", "status"),
        Index("ix_investigations_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    entry_type: Mapped[InvestigationEntryType] = mapped_column(
        Enum(InvestigationEntryType), default=InvestigationEntryType.AUTOMATIC
    )
    starting_transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True)
    starting_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    scenario_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenario_runs.id"), nullable=True)
    scenario_id: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus), default=InvestigationStatus.OPEN
    )
    title: Mapped[str] = mapped_column(String(300), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    graph_data: Mapped[str] = mapped_column(Text, nullable=True)  # JSON NetworkX export
    max_depth_forward: Mapped[int] = mapped_column(Integer, default=4)
    max_depth_backward: Mapped[int] = mapped_column(Integer, default=4)
    time_window_days: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    investigator_notes: Mapped[str] = mapped_column(Text, nullable=True)

    starting_transaction: Mapped["Transaction"] = relationship("Transaction", foreign_keys=[starting_transaction_id])
    starting_account: Mapped["Account"] = relationship("Account", foreign_keys=[starting_account_id])
    alerts: Mapped[list["RiskAlert"]] = relationship("RiskAlert", back_populates="investigation")
    scenario_run: Mapped["ScenarioRun"] = relationship("ScenarioRun", back_populates="investigation")


# ─────────────────────────────────────────────────────────────────────────────
# Risk Alerts
# ─────────────────────────────────────────────────────────────────────────────

class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    __table_args__ = (
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_investigation", "investigation_id"),
        Index("ix_alerts_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=True)
    triggering_transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True)
    relevant_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), default=AlertSeverity.MEDIUM)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.OPEN)
    risk_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    evidence: Mapped[str] = mapped_column(Text, nullable=True)  # JSON evidence list
    resolution_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="alerts")
    triggering_transaction: Mapped["Transaction"] = relationship("Transaction", foreign_keys=[triggering_transaction_id])
    relevant_account: Mapped["Account"] = relationship("Account", foreign_keys=[relevant_account_id])


# ─────────────────────────────────────────────────────────────────────────────
# Scenario Runs
# ─────────────────────────────────────────────────────────────────────────────

class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    scenario_id: Mapped[str] = mapped_column(String(50), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ScenarioRunStatus] = mapped_column(
        Enum(ScenarioRunStatus), default=ScenarioRunStatus.PENDING
    )
    parameters: Mapped[str] = mapped_column(Text, nullable=True)  # JSON
    seed: Mapped[int] = mapped_column(Integer, nullable=True)
    num_accounts: Mapped[int] = mapped_column(Integer, nullable=True)
    num_transactions: Mapped[int] = mapped_column(Integer, nullable=True)
    transactions_created: Mapped[int] = mapped_column(Integer, default=0)
    accounts_created: Mapped[int] = mapped_column(Integer, default=0)
    alerts_generated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="scenario_run", uselist=False)
    ground_truth: Mapped[list["ScenarioGroundTruth"]] = relationship("ScenarioGroundTruth", back_populates="scenario_run")


class ScenarioGroundTruth(Base):
    """Isolated ground-truth labels — never exposed to the detection engine."""
    __tablename__ = "scenario_ground_truth"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    scenario_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenario_runs.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ACCOUNT, TRANSACTION
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # MULE, VICTIM, KINGPIN, NORMAL, etc.
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    scenario_run: Mapped["ScenarioRun"] = relationship("ScenarioRun", back_populates="ground_truth")


# ─────────────────────────────────────────────────────────────────────────────
# Normalisation Records
# ─────────────────────────────────────────────────────────────────────────────

class NormalisationRecord(Base):
    __tablename__ = "normalisation_records"
    __table_args__ = (
        Index("ix_norm_bank", "bank_id"),
        Index("ix_norm_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    bank_id: Mapped[str] = mapped_column(String(36), ForeignKey("banks.id"), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACCEPTED")  # ACCEPTED, REJECTED, DUPLICATE, WARNING
    schema_version: Mapped[str] = mapped_column(String(20), nullable=True)
    adapter_used: Mapped[str] = mapped_column(String(100), nullable=True)
    errors: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list of error strings
    warnings: Mapped[str] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=True)
    canonical_transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Off-Ramp Events
# ─────────────────────────────────────────────────────────────────────────────

class OffRampEvent(Base):
    __tablename__ = "off_ramp_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    transaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("transactions.id"), nullable=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)
    off_ramp_type: Mapped[str] = mapped_column(String(100), nullable=False)  # CASH_WITHDRAWAL, CONVERSION, ASSET_PURCHASE, CONSOLIDATION
    attempted_amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), nullable=False)
    attributed_suspicious_amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 4), default=Decimal("0"))
    status: Mapped[OffRampStatus] = mapped_column(Enum(OffRampStatus), default=OffRampStatus.OBSERVED)
    risk_signals: Mapped[str] = mapped_column(Text, nullable=True)  # JSON
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Audit Events
# ─────────────────────────────────────────────────────────────────────────────

class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_created", "created_at"),
        Index("ix_audit_event_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)  # extra structured info
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
