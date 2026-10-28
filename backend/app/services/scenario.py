"""
Scenario Service — runs a chosen scenario through the full pipeline:
1. Generates synthetic data
2. Normalises through bank adapters
3. Persists accounts, transactions, ground truth to MySQL
4. Creates investigation
5. Runs investigation engine
6. Returns results
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    Bank, Account, AccountBaseline, Transaction, ScenarioRun, ScenarioGroundTruth,
    NormalisationRecord, AuditEvent, Investigation, ProvenanceRecord, ProvenanceMovement,
    TransactionStatus, ScenarioRunStatus, ProvenanceMode, ProvenanceStatus, AllocationMethod,
    InvestigationEntryType,
)
from app.adapters.registry import get_adapter
from app.services.generator import (
    SyntheticGenerator, SyntheticAccount, SyntheticTransaction, GeneratorResult,
)
from app.services.investigation import create_investigation, run_investigation


SCENARIO_META = {
    "scenario_1": {
        "name": "Conventional Money Transfer Trace",
        "description": (
            "A victim reports a suspicious transaction. "
            "The system traces money through mule accounts across banks "
            "to identify the potential beneficiary."
        ),
    },
    "scenario_2": {
        "name": "Simulated CBDC Token Lineage",
        "description": (
            "Demonstrates the proposed CBDC token-lineage model. "
            "A parent provenance record (₹5L) splits into P1 (₹2L) and P2 (₹3L). "
            "P1 further splits into P1A (₹50K) and P1B (₹1.5L)."
        ),
    },
    "scenario_3": {
        "name": "Pre-positioned Transfers & Delayed Replenishment",
        "description": (
            "B and C pre-position ₹2L each to D on Day 0. "
            "A victim transfers ₹4L to A on Day 2. "
            "A replenishes B and C on Day 3. "
            "Backward investigation discovers the earlier B→D and C→D transfers."
        ),
    },
    "scenario_4": {
        "name": "Fragmented Value Below High-Value Threshold",
        "description": (
            "A victim's ₹9.6L loss is split into 8 transfers of ₹1.2L each "
            "(all below the ₹10L threshold). "
            "The system screens, connects, and aggregates the linked activity."
        ),
    },
}


async def get_or_create_banks(db: AsyncSession) -> dict[str, Bank]:
    """Ensure all four banks exist in the database."""
    bank_defs = [
        {"bank_code": "BANK_A", "display_name": "Apex National Bank", "native_schema_version": "A_v1.0", "description": "Native format: txn_id/sender/receiver/amount/timestamp"},
        {"bank_code": "BANK_B", "display_name": "Bharat Commercial Bank", "native_schema_version": "B_v2.1", "description": "Native format: reference/debit_acct/credit_acct/txn_amount/txn_date (IST)"},
        {"bank_code": "BANK_C", "display_name": "Continental Finance Ltd", "native_schema_version": "C_v1.5", "description": "Native format: id/from_account/to_account/value_paise/event_time (Unix epoch)"},
        {"bank_code": "BANK_D", "display_name": "Dhanvantari International", "native_schema_version": "D_v3.0", "description": "Native format: msg_id/ordering_account/beneficiary_account/instructed_amount/value_date (YYYYMMDD)"},
    ]
    banks: dict[str, Bank] = {}
    for bdef in bank_defs:
        result = await db.execute(select(Bank).where(Bank.bank_code == bdef["bank_code"]))
        bank = result.scalar_one_or_none()
        if bank is None:
            bank = Bank(id=str(uuid.uuid4()), **bdef)
            db.add(bank)
            await db.flush()
        banks[bdef["bank_code"]] = bank
    return banks


async def run_scenario(
    db: AsyncSession,
    scenario_id: str,
    seed: int = 42,
    timespan_days: int = 30,
    run_id: str | None = None,
) -> dict:
    """Execute a full scenario: generate → normalise → persist → investigate."""
    meta = SCENARIO_META.get(scenario_id)
    if meta is None:
        raise ValueError(f"Unknown scenario: {scenario_id}")

    # Create run record
    run = ScenarioRun(
        id=run_id or str(uuid.uuid4()),
        scenario_id=scenario_id,
        scenario_name=meta["name"],
        status=ScenarioRunStatus.RUNNING,
        seed=seed,
        parameters=json.dumps({"seed": seed, "timespan_days": timespan_days}),
    )
    db.add(run)
    await db.flush()

    try:
        banks = await get_or_create_banks(db)
        gen = SyntheticGenerator(seed=seed, timespan_days=timespan_days)

        # Generate scenario data
        gen_fn = {
            "scenario_1": gen.generate_scenario_1,
            "scenario_2": gen.generate_scenario_2,
            "scenario_3": gen.generate_scenario_3,
            "scenario_4": gen.generate_scenario_4,
        }[scenario_id]
        result: GeneratorResult = gen_fn()

        # Persist accounts
        account_map: dict[str, Account] = {}  # account_ref → Account
        for syn_acc in result.accounts:
            bank = banks.get(syn_acc.bank_code)
            if bank is None:
                continue
            # Dedup: check if account_ref already exists for this bank
            existing = await db.execute(
                select(Account).where(
                    Account.bank_id == bank.id,
                    Account.account_ref == syn_acc.account_ref,
                )
            )
            acc = existing.scalar_one_or_none()
            if acc is None:
                acc = Account(
                    id=syn_acc.id,
                    bank_id=bank.id,
                    account_ref=syn_acc.account_ref,
                    account_type=syn_acc.account_type,
                    owner_name=syn_acc.owner_name,
                    opening_balance=syn_acc.opening_balance,
                    current_balance=syn_acc.balance,
                    currency=syn_acc.currency,
                    simulated_device_id=syn_acc.simulated_device_id,
                    simulated_ip=syn_acc.simulated_ip,
                )
                db.add(acc)
                # Baseline
                baseline = AccountBaseline(
                    id=str(uuid.uuid4()),
                    account_id=acc.id,
                    avg_transaction_amount=syn_acc.opening_balance / Decimal("10"),
                    avg_monthly_volume=syn_acc.opening_balance,
                    max_single_transaction=syn_acc.opening_balance / Decimal("2"),
                )
                db.add(baseline)
                await db.flush()
            account_map[syn_acc.account_ref] = acc
        run.accounts_created = len(account_map)

        # Normalise and persist transactions
        txn_count = 0
        for syn_txn in result.transactions:
            bank = banks.get(syn_txn.bank_code)
            if bank is None:
                continue
            adapter = get_adapter(syn_txn.bank_code, bank.id)
            norm_result = adapter.normalise(syn_txn.native_record)

            # Record normalisation
            norm_rec = NormalisationRecord(
                id=str(uuid.uuid4()),
                bank_id=bank.id,
                source_reference=norm_result.source_reference,
                status=norm_result.status,
                schema_version=adapter.schema_version,
                adapter_used=adapter.adapter_used,
                errors=json.dumps(norm_result.errors),
                warnings=json.dumps(norm_result.warnings),
                raw_payload=norm_result.raw_payload[:2000] if norm_result.raw_payload else None,
            )

            if norm_result.canonical:
                can = norm_result.canonical
                sender_acc = account_map.get(syn_txn.sender_ref)
                receiver_acc = account_map.get(syn_txn.receiver_ref)

                txn = Transaction(
                    id=syn_txn.id,
                    transaction_ref=can.source_reference,
                    source_reference=can.source_reference,
                    bank_id=bank.id,
                    source_bank_id=bank.id,
                    sender_account_id=sender_acc.id if sender_acc else None,
                    receiver_account_id=receiver_acc.id if receiver_acc else None,
                    sender_account_ref=can.sender_account_ref,
                    receiver_account_ref=can.receiver_account_ref,
                    amount=can.amount,
                    currency=can.currency,
                    timestamp_utc=can.timestamp_utc,
                    status=TransactionStatus.COMPLETED,
                    schema_version=can.schema_version,
                    adapter_used=can.adapter_used,
                    scenario_run_id=run.id,
                    raw_payload=can.raw_payload[:2000] if can.raw_payload else None,
                )
                db.add(txn)
                await db.flush()
                norm_rec.canonical_transaction_id = txn.id
                txn_count += 1

            db.add(norm_rec)

        await db.flush()
        run.transactions_created = txn_count

        # Persist ground truth (isolated)
        for gt_entry in result.ground_truth:
            gt = ScenarioGroundTruth(
                id=str(uuid.uuid4()),
                scenario_run_id=run.id,
                entity_type=gt_entry["entity_type"],
                entity_id=gt_entry["entity_id"],
                label=gt_entry["label"],
                notes=gt_entry.get("notes", ""),
            )
            db.add(gt)

        # For Scenario 2: create CBDC provenance records
        if scenario_id == "scenario_2":
            await _create_scenario2_provenance(db, run.id, result, account_map, banks)

        # Create and run investigation
        entry_type = "REPORTED_FRAUD" if scenario_id in ("scenario_1", "scenario_3", "scenario_4") else "AUTOMATIC"
        inv = await create_investigation(
            db,
            entry_type=entry_type,
            scenario_run_id=run.id,
            scenario_id=scenario_id,
            title=f"{meta['name']} — Run {run.id[:8]}",
        )

        # For reported-fraud scenarios, set starting transaction
        if scenario_id in ("scenario_1", "scenario_3", "scenario_4"):
            victim_txn = await _find_victim_transaction(db, run.id, result)
            if victim_txn:
                inv.starting_transaction_id = victim_txn.id
                inv.starting_account_id = victim_txn.receiver_account_id
                await db.flush()

        investigation_result = await run_investigation(db, inv.id)
        run.alerts_generated = investigation_result.get("alerts_created", 0)
        run.status = ScenarioRunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)

        await _log_audit(db, "SCENARIO_COMPLETED", "scenario_run", run.id,
                         f"Scenario {scenario_id} completed: {txn_count} transactions, "
                         f"{investigation_result.get('alerts_created', 0)} alerts")

        return {
            "run_id": run.id,
            "scenario_id": scenario_id,
            "scenario_name": meta["name"],
            "status": "COMPLETED",
            "accounts_created": run.accounts_created,
            "transactions_created": txn_count,
            "alerts_generated": run.alerts_generated,
            "investigation_id": inv.id,
            "investigation_summary": investigation_result,
            "generator_errors": result.errors,
        }

    except Exception as exc:
        run.status = ScenarioRunStatus.FAILED
        run.error_message = str(exc)[:500]
        await db.flush()
        raise


async def reset_scenario_run(db: AsyncSession, run_id: str) -> dict:
    """Delete all data created by a specific scenario run."""
    from sqlalchemy import delete
    from app.models import NormalisationRecord

    # Delete transactions
    await db.execute(
        delete(Transaction).where(Transaction.scenario_run_id == run_id)
    )
    # Delete ground truth
    await db.execute(
        delete(ScenarioGroundTruth).where(ScenarioGroundTruth.scenario_run_id == run_id)
    )
    # Update run status
    result = await db.execute(select(ScenarioRun).where(ScenarioRun.id == run_id))
    run = result.scalar_one_or_none()
    if run:
        run.status = ScenarioRunStatus.RESET
        run.transactions_created = 0
        run.accounts_created = 0
        run.alerts_generated = 0

    await db.flush()
    await _log_audit(db, "SCENARIO_RESET", "scenario_run", run_id, "Scenario run reset")
    return {"run_id": run_id, "status": "RESET"}


async def _find_victim_transaction(
    db: AsyncSession, run_id: str, result: GeneratorResult
) -> Transaction | None:
    """Find the victim-to-mule transaction for reported-fraud scenarios."""
    victim_labels = {gt["entity_id"] for gt in result.ground_truth if gt["label"] == "VICTIM"}
    mule_labels = {gt["entity_id"] for gt in result.ground_truth if gt["label"] == "MULE"}

    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.scenario_run_id == run_id,
            Transaction.sender_account_ref.in_(victim_labels),
            Transaction.receiver_account_ref.in_(mule_labels),
        ).order_by(Transaction.timestamp_utc).limit(1)
    )
    return txn_result.scalar_one_or_none()


async def _create_scenario2_provenance(
    db: AsyncSession, run_id: str,
    result: GeneratorResult,
    account_map: dict[str, "Account"],
    banks: dict[str, "Bank"],
):
    """Create CBDC parent-child provenance records for Scenario 2."""
    cbdc_accounts = {
        gt["entity_id"]: gt["label"]
        for gt in result.ground_truth
        if gt["label"].startswith("CBDC")
    }

    origin_ref = next((ref for ref, lbl in cbdc_accounts.items() if lbl == "CBDC_ORIGIN"), None)
    if not origin_ref:
        return

    origin_acc = account_map.get(origin_ref)
    if not origin_acc:
        return

    # Create root provenance
    root_id = str(uuid.uuid4())
    root = ProvenanceRecord(
        id=root_id,
        parent_id=None,
        mode=ProvenanceMode.CBDC_LINEAGE,
        initial_amount=Decimal("500000"),
        attributed_amount=Decimal("500000"),
        remaining_amount=Decimal("0"),  # split into P1+P2
        currency="INR",
        current_holder_account_id=origin_acc.id,
        allocation_method=AllocationMethod.FIFO,
        status=ProvenanceStatus.SPLIT,
        investigation_id=None,
        notes="Simulated CBDC root provenance — ₹5L origin",
    )
    db.add(root)
    await db.flush()

    # P1 and P2
    p1_ref = next((ref for ref, lbl in cbdc_accounts.items() if lbl == "CBDC_INTERMEDIATE" and "P1" in ref[:20]), None)
    p2_ref = next((ref for ref, lbl in cbdc_accounts.items() if lbl == "CBDC_INTERMEDIATE" and "P2" in ref[:20]), None)

    p1_id = str(uuid.uuid4())
    p2_id = str(uuid.uuid4())

    for pid, ref, amt, notes in [
        (p1_id, p1_ref, Decimal("200000"), "P1 — ₹2L child"),
        (p2_id, p2_ref, Decimal("300000"), "P2 — ₹3L child"),
    ]:
        acc = account_map.get(ref) if ref else None
        child = ProvenanceRecord(
            id=pid,
            parent_id=root_id,
            mode=ProvenanceMode.CBDC_LINEAGE,
            initial_amount=amt,
            attributed_amount=amt,
            remaining_amount=amt if pid == p2_id else Decimal("0"),
            currency="INR",
            current_holder_account_id=acc.id if acc else None,
            allocation_method=AllocationMethod.FIFO,
            status=ProvenanceStatus.SPLIT if pid == p1_id else ProvenanceStatus.ACTIVE,
            notes=notes,
        )
        db.add(child)
        await db.flush()

    # P1A and P1B
    leaf_refs = [(ref, lbl) for ref, lbl in cbdc_accounts.items() if lbl == "CBDC_LEAF"]
    leaf_configs = [
        (Decimal("50000"), "P1A — ₹50K leaf"),
        (Decimal("150000"), "P1B — ₹1.5L leaf"),
    ]
    for (ref, lbl), (amt, notes) in zip(leaf_refs, leaf_configs):
        acc = account_map.get(ref)
        leaf = ProvenanceRecord(
            id=str(uuid.uuid4()),
            parent_id=p1_id,
            mode=ProvenanceMode.CBDC_LINEAGE,
            initial_amount=amt,
            attributed_amount=amt,
            remaining_amount=amt,
            currency="INR",
            current_holder_account_id=acc.id if acc else None,
            allocation_method=AllocationMethod.FIFO,
            status=ProvenanceStatus.ACTIVE,
            notes=notes,
        )
        db.add(leaf)

    await db.flush()


async def _log_audit(
    db: AsyncSession, event_type: str, entity_type: str,
    entity_id: str, description: str,
):
    audit = AuditEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(audit)
    await db.flush()
