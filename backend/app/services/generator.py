"""
Mule Matrix Synthetic Transaction Generator.

Generates deterministic, configurable synthetic transactions for four scenarios.
Ground-truth labels are stored separately and never exposed to the detection engine.
All balances are validated before each transaction is created.
"""
from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Data classes for in-memory synthetic generation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SyntheticAccount:
    id: str
    bank_code: str
    account_ref: str
    account_type: str
    owner_name: str
    balance: Decimal
    opening_balance: Decimal
    currency: str = "INR"
    simulated_device_id: str | None = None
    simulated_ip: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def debit(self, amount: Decimal) -> bool:
        if self.balance < amount:
            return False
        self.balance -= amount
        return True

    def credit(self, amount: Decimal):
        self.balance += amount


@dataclass
class SyntheticTransaction:
    id: str
    native_record: dict[str, Any]
    bank_code: str
    sender_ref: str
    receiver_ref: str
    amount: Decimal
    currency: str
    timestamp_utc: datetime
    status: str
    scenario_label: str = ""  # ground-truth label (not exposed to detection)


@dataclass
class GeneratorResult:
    banks: list[dict]
    accounts: list[SyntheticAccount]
    transactions: list[SyntheticTransaction]
    ground_truth: list[dict]  # {entity_type, entity_id (ref), label, notes}
    errors: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# Helper: native record builders per bank format
# ─────────────────────────────────────────────────────────────────────────────

def _build_bank_a_record(txn_id: str, sender: str, receiver: str,
                          amount: Decimal, ts: datetime, status: str = "SUCCESS") -> dict:
    return {
        "txn_id": txn_id,
        "sender": sender,
        "receiver": receiver,
        "amount": str(amount),
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
    }


def _build_bank_b_record(reference: str, debit_acct: str, credit_acct: str,
                          amount: Decimal, ts: datetime, status: str = "SETTLED") -> dict:
    ist = ts.astimezone(timezone(timedelta(hours=5, minutes=30)))
    return {
        "reference": reference,
        "debit_acct": debit_acct,
        "credit_acct": credit_acct,
        "txn_amount": str(amount),
        "txn_date": ist.strftime("%Y-%m-%d %H:%M:%S"),
        "txn_status": status,
    }


def _build_bank_c_record(record_id: str, from_account: str, to_account: str,
                          amount: Decimal, ts: datetime, status: str = "SUCCESS") -> dict:
    paise = int(amount * 100)
    return {
        "id": record_id,
        "from_account": from_account,
        "to_account": to_account,
        "value_paise": paise,
        "event_time": int(ts.timestamp()),
        "event_status": status,
    }


def _build_bank_d_record(msg_id: str, ordering: str, beneficiary: str,
                          amount: Decimal, ts: datetime, status: str = "ACSC",
                          currency: str = "INR") -> dict:
    return {
        "msg_id": msg_id,
        "ordering_account": ordering,
        "beneficiary_account": beneficiary,
        "instructed_amount": str(amount),
        "instructed_currency": currency,
        "value_date": ts.strftime("%Y%m%d"),
        "msg_status": status,
        "transaction_type": "CREDIT_TRANSFER",
    }


BANK_RECORD_BUILDERS = {
    "BANK_A": _build_bank_a_record,
    "BANK_B": _build_bank_b_record,
    "BANK_C": _build_bank_c_record,
    "BANK_D": _build_bank_d_record,
}

BANK_STATUSES = {
    "BANK_A": "SUCCESS",
    "BANK_B": "SETTLED",
    "BANK_C": "SUCCESS",
    "BANK_D": "ACSC",
}

BANK_CODES = ["BANK_A", "BANK_B", "BANK_C", "BANK_D"]


# ─────────────────────────────────────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────────────────────────────────────

class SyntheticGenerator:

    def __init__(self, seed: int = 42, timespan_days: int = 30):
        self.rng = random.Random(seed)
        self.seed = seed
        self.start_time = datetime.now(timezone.utc) - timedelta(days=timespan_days)
        self.timespan_days = timespan_days
        self._txn_counter = 0

    # ── utilities ──────────────────────────────────────────────────────────

    def _random_ts(self, after: datetime | None = None, before: datetime | None = None) -> datetime:
        lo = after or self.start_time
        hi = before or (self.start_time + timedelta(days=self.timespan_days))
        if lo >= hi:
            hi = lo + timedelta(hours=1)
        delta = (hi - lo).total_seconds()
        offset = self.rng.uniform(0, delta)
        return lo + timedelta(seconds=offset)

    def _ts_at_day(self, day_offset: float, hour: int = 10) -> datetime:
        return self.start_time + timedelta(days=day_offset, hours=hour)

    def _amount(self, lo: float, hi: float) -> Decimal:
        raw = self.rng.uniform(lo, hi)
        return Decimal(str(round(raw, 2)))

    def _next_ref(self, prefix: str = "TXN") -> str:
        self._txn_counter += 1
        return f"{prefix}{self._txn_counter:08d}"

    def _make_account(self, bank_code: str, acc_type: str, owner: str,
                      balance: float) -> SyntheticAccount:
        acc_ref = f"{bank_code[:1]}{self.rng.randint(10000000, 99999999)}"
        device_id = f"DEV-{self.rng.randint(1000, 9999)}"
        ip = f"10.{self.rng.randint(0,255)}.{self.rng.randint(0,255)}.{self.rng.randint(1,254)}"
        bal = Decimal(str(round(balance, 2)))
        return SyntheticAccount(
            id=str(uuid.uuid4()),
            bank_code=bank_code,
            account_ref=acc_ref,
            account_type=acc_type,
            owner_name=owner,
            balance=bal,
            opening_balance=bal,
            simulated_device_id=device_id,
            simulated_ip=ip,
        )

    def _transfer(self, sender: SyntheticAccount, receiver: SyntheticAccount,
                  amount: Decimal, ts: datetime,
                  label: str = "NORMAL") -> SyntheticTransaction | None:
        """Create a transfer. Returns None if sender has insufficient balance."""
        if not sender.debit(amount):
            return None
        receiver.credit(amount)
        ref = self._next_ref()
        bank_code = sender.bank_code
        builder = BANK_RECORD_BUILDERS[bank_code]
        native = builder(ref, sender.account_ref, receiver.account_ref,
                         amount, ts, BANK_STATUSES[bank_code])
        return SyntheticTransaction(
            id=str(uuid.uuid4()),
            native_record=native,
            bank_code=bank_code,
            sender_ref=sender.account_ref,
            receiver_ref=receiver.account_ref,
            amount=amount,
            currency="INR",
            timestamp_utc=ts,
            status="COMPLETED",
            scenario_label=label,
        )

    # ── Normal background activity ─────────────────────────────────────────

    def generate_normal_accounts(self, count: int) -> list[SyntheticAccount]:
        accounts = []
        names = [
            "Rajan Kumar", "Priya Sharma", "Anand Patel", "Sunita Reddy",
            "Vijay Singh", "Meena Nair", "Arun Joshi", "Kavita Mehta",
            "Suresh Iyer", "Deepa Verma", "Mohan Das", "Lalitha Rao",
        ]
        for i in range(count):
            bank_code = BANK_CODES[i % 4]
            name = names[i % len(names)] + f" {i}"
            balance = self.rng.uniform(50_000, 500_000)
            acc = self._make_account(bank_code, "SAVINGS", name, balance)
            accounts.append(acc)
        return accounts

    def generate_normal_transactions(
        self, accounts: list[SyntheticAccount], count: int
    ) -> tuple[list[SyntheticTransaction], list[str]]:
        txns = []
        errors = []
        for _ in range(count):
            sender = self.rng.choice(accounts)
            receiver = self.rng.choice(accounts)
            if sender.account_ref == receiver.account_ref:
                continue
            amount = self._amount(500, 50_000)
            ts = self._random_ts()
            t = self._transfer(sender, receiver, amount, ts, "NORMAL")
            if t is None:
                errors.append(f"Insufficient balance: {sender.account_ref} for {amount}")
            else:
                txns.append(t)
        return txns, errors

    # ── Scenario generation ────────────────────────────────────────────────

    def generate_scenario_1(self) -> GeneratorResult:
        """Conventional money transfer: Victim → Mule A → {Mule B, Mule C} → beneficiary/off-ramp."""
        accounts = self.generate_normal_accounts(20)
        txns, errors = self.generate_normal_transactions(accounts, 80)
        gt = []

        # Scenario accounts
        victim = self._make_account("BANK_A", "SAVINGS", "Victim S1", 1_000_000)
        mule_a = self._make_account("BANK_B", "SAVINGS", "Mule A S1", 10_000)
        mule_b = self._make_account("BANK_C", "SAVINGS", "Mule B S1", 5_000)
        mule_c = self._make_account("BANK_C", "SAVINGS", "Mule C S1", 5_000)
        beneficiary = self._make_account("BANK_D", "SAVINGS", "Beneficiary S1", 50_000)
        all_accounts = accounts + [victim, mule_a, mule_b, mule_c, beneficiary]

        day = 10
        # Victim reports suspicious transaction
        t1 = self._transfer(victim, mule_a, Decimal("400000"), self._ts_at_day(day, 9), "VICTIM_TO_MULE")
        day += 0.2
        t2 = self._transfer(mule_a, mule_b, Decimal("180000"), self._ts_at_day(day, 10), "MULE_PASSTHROUGH")
        t3 = self._transfer(mule_a, mule_c, Decimal("150000"), self._ts_at_day(day, 11), "MULE_PASSTHROUGH")
        day += 0.5
        t4 = self._transfer(mule_b, beneficiary, Decimal("175000"), self._ts_at_day(day, 9), "MULE_TO_BENEFICIARY")
        t5 = self._transfer(mule_c, beneficiary, Decimal("140000"), self._ts_at_day(day, 14), "MULE_TO_BENEFICIARY")

        for t in [t1, t2, t3, t4, t5]:
            if t:
                txns.append(t)

        gt += [
            {"entity_type": "ACCOUNT", "entity_id": victim.account_ref, "label": "VICTIM", "notes": "Reported fraud"},
            {"entity_type": "ACCOUNT", "entity_id": mule_a.account_ref, "label": "MULE", "notes": "Pass-through"},
            {"entity_type": "ACCOUNT", "entity_id": mule_b.account_ref, "label": "MULE", "notes": "Fan-out leg"},
            {"entity_type": "ACCOUNT", "entity_id": mule_c.account_ref, "label": "MULE", "notes": "Fan-out leg"},
            {"entity_type": "ACCOUNT", "entity_id": beneficiary.account_ref, "label": "POTENTIAL_BENEFICIARY", "notes": "Convergence"},
        ]
        if t1:
            gt.append({"entity_type": "TRANSACTION", "entity_id": t1.id, "label": "REPORTED_FRAUD", "notes": "Victim-reported"})

        return GeneratorResult(
            banks=[{"code": c} for c in BANK_CODES],
            accounts=all_accounts,
            transactions=txns,
            ground_truth=gt,
            errors=errors,
        )

    def generate_scenario_2(self) -> GeneratorResult:
        """Simulated CBDC token lineage: parent ₹5L → P1 ₹2L + P2 ₹3L → P1→(P1A ₹50K + P1B ₹1.5L)."""
        accounts = self.generate_normal_accounts(15)
        txns, errors = self.generate_normal_transactions(accounts, 60)
        gt = []

        origin_holder = self._make_account("BANK_A", "CBDC_WALLET", "CBDC Origin S2", 600_000)
        holder_p1 = self._make_account("BANK_B", "CBDC_WALLET", "CBDC P1 Holder S2", 10_000)
        holder_p2 = self._make_account("BANK_C", "CBDC_WALLET", "CBDC P2 Holder S2", 10_000)
        holder_p1a = self._make_account("BANK_D", "CBDC_WALLET", "CBDC P1A Holder S2", 5_000)
        holder_p1b = self._make_account("BANK_A", "CBDC_WALLET", "CBDC P1B Holder S2", 5_000)
        all_accounts = accounts + [origin_holder, holder_p1, holder_p2, holder_p1a, holder_p1b]

        day = 5
        t_origin = self._transfer(origin_holder, holder_p1, Decimal("200000"), self._ts_at_day(day, 9), "CBDC_TRANSFER")
        day += 0.1
        t_p2 = self._transfer(origin_holder, holder_p2, Decimal("300000"), self._ts_at_day(day, 10), "CBDC_TRANSFER")
        day += 2
        t_p1a = self._transfer(holder_p1, holder_p1a, Decimal("50000"), self._ts_at_day(day, 9), "CBDC_SPLIT")
        day += 0.1
        t_p1b = self._transfer(holder_p1, holder_p1b, Decimal("150000"), self._ts_at_day(day, 11), "CBDC_SPLIT")

        for t in [t_origin, t_p2, t_p1a, t_p1b]:
            if t:
                txns.append(t)

        gt += [
            {"entity_type": "ACCOUNT", "entity_id": origin_holder.account_ref, "label": "CBDC_ORIGIN", "notes": "₹5L source"},
            {"entity_type": "ACCOUNT", "entity_id": holder_p1.account_ref, "label": "CBDC_INTERMEDIATE", "notes": "P1 ₹2L"},
            {"entity_type": "ACCOUNT", "entity_id": holder_p2.account_ref, "label": "CBDC_INTERMEDIATE", "notes": "P2 ₹3L"},
            {"entity_type": "ACCOUNT", "entity_id": holder_p1a.account_ref, "label": "CBDC_LEAF", "notes": "P1A ₹50K"},
            {"entity_type": "ACCOUNT", "entity_id": holder_p1b.account_ref, "label": "CBDC_LEAF", "notes": "P1B ₹1.5L"},
        ]

        return GeneratorResult(
            banks=[{"code": c} for c in BANK_CODES],
            accounts=all_accounts,
            transactions=txns,
            ground_truth=gt,
            errors=errors,
        )

    def generate_scenario_3(self) -> GeneratorResult:
        """Pre-positioned transfers and delayed replenishment.
        Day 0: B→D ₹2L, C→D ₹2L
        Day 2: Victim→A ₹4L
        Day 3: A→B ₹2L, A→C ₹2L
        """
        accounts = self.generate_normal_accounts(20)
        txns, errors = self.generate_normal_transactions(accounts, 90)
        gt = []

        victim = self._make_account("BANK_A", "SAVINGS", "Victim S3", 500_000)
        mule_a = self._make_account("BANK_B", "SAVINGS", "Mule A S3", 50_000)
        mule_b = self._make_account("BANK_C", "SAVINGS", "Mule B S3", 250_000)
        mule_c = self._make_account("BANK_D", "SAVINGS", "Mule C S3", 250_000)
        suspect_d = self._make_account("BANK_A", "SAVINGS", "Suspect D S3", 100_000)
        all_accounts = accounts + [victim, mule_a, mule_b, mule_c, suspect_d]

        base_day = 5  # offset within the generated time window
        # Day 0: B→D and C→D (pre-positioned, before any victim transaction)
        t_bd = self._transfer(mule_b, suspect_d, Decimal("200000"), self._ts_at_day(base_day + 0, 9), "PRE_POSITION")
        t_cd = self._transfer(mule_c, suspect_d, Decimal("200000"), self._ts_at_day(base_day + 0, 14), "PRE_POSITION")

        # Day 2: Victim→A (reported fraud)
        t_va = self._transfer(victim, mule_a, Decimal("400000"), self._ts_at_day(base_day + 2, 10), "VICTIM_TO_MULE")

        # Day 3: A→B, A→C (replenishment)
        t_ab = self._transfer(mule_a, mule_b, Decimal("200000"), self._ts_at_day(base_day + 3, 9), "REPLENISHMENT")
        t_ac = self._transfer(mule_a, mule_c, Decimal("200000"), self._ts_at_day(base_day + 3, 11), "REPLENISHMENT")

        for t in [t_bd, t_cd, t_va, t_ab, t_ac]:
            if t:
                txns.append(t)
            else:
                errors.append("Scenario 3: transfer rejected due to insufficient balance")

        gt += [
            {"entity_type": "ACCOUNT", "entity_id": victim.account_ref, "label": "VICTIM", "notes": "Day 2 victim"},
            {"entity_type": "ACCOUNT", "entity_id": mule_a.account_ref, "label": "MULE", "notes": "Receives victim funds"},
            {"entity_type": "ACCOUNT", "entity_id": mule_b.account_ref, "label": "MULE", "notes": "Pre-positioned; receives replenishment"},
            {"entity_type": "ACCOUNT", "entity_id": mule_c.account_ref, "label": "MULE", "notes": "Pre-positioned; receives replenishment"},
            {"entity_type": "ACCOUNT", "entity_id": suspect_d.account_ref, "label": "POTENTIAL_KINGPIN", "notes": "Receives pre-positioned funds; evidence-based only"},
        ]
        if t_va:
            gt.append({"entity_type": "TRANSACTION", "entity_id": t_va.id, "label": "REPORTED_FRAUD", "notes": "Victim-reported Day 2"})

        return GeneratorResult(
            banks=[{"code": c} for c in BANK_CODES],
            accounts=all_accounts,
            transactions=txns,
            ground_truth=gt,
            errors=errors,
        )

    def generate_scenario_4(self) -> GeneratorResult:
        """Fragmented value below threshold: ₹9.6L split into 8 transfers of ₹1.2L each."""
        accounts = self.generate_normal_accounts(20)
        txns, errors = self.generate_normal_transactions(accounts, 100)
        gt = []

        threshold = Decimal("1000000")  # ₹10L high-value threshold
        fragment_amount = Decimal("120000")  # ₹1.2L each — below threshold
        num_fragments = 8

        victim = self._make_account("BANK_A", "SAVINGS", "Victim S4", 1_000_000)
        # Create intermediate mule accounts
        intermediates = [
            self._make_account(BANK_CODES[i % 4], "SAVINGS", f"Intermediate S4-{i}", 10_000)
            for i in range(num_fragments)
        ]
        collector = self._make_account("BANK_D", "SAVINGS", "Collector S4", 50_000)
        all_accounts = accounts + [victim] + intermediates + [collector]

        base_day = 8
        fragment_txns = []
        for i, inter in enumerate(intermediates):
            ts = self._ts_at_day(base_day, 9 + i * 0.5)
            t = self._transfer(victim, inter, fragment_amount, ts, "FRAGMENT")
            if t:
                fragment_txns.append(t)
                txns.append(t)

        # Each intermediate forwards to collector (slightly later)
        for i, inter in enumerate(intermediates):
            ts = self._ts_at_day(base_day + 0.5, 9 + i * 0.5)
            forward_amount = fragment_amount - self._amount(100, 500)  # slight variation
            t = self._transfer(inter, collector, forward_amount, ts, "FRAGMENT_FORWARD")
            if t:
                txns.append(t)

        gt += [
            {"entity_type": "ACCOUNT", "entity_id": victim.account_ref, "label": "VICTIM", "notes": "₹9.6L split source"},
            {"entity_type": "ACCOUNT", "entity_id": collector.account_ref, "label": "POTENTIAL_BENEFICIARY", "notes": "Convergence collector"},
        ]
        for inter in intermediates:
            gt.append({"entity_type": "ACCOUNT", "entity_id": inter.account_ref, "label": "MULE", "notes": "Fragment mule"})

        return GeneratorResult(
            banks=[{"code": c} for c in BANK_CODES],
            accounts=all_accounts,
            transactions=txns,
            ground_truth=gt,
            errors=errors,
        )

    def generate_background_normal(
        self, num_accounts: int = 40, num_transactions: int = 200
    ) -> GeneratorResult:
        """Pure normal activity for dashboard background."""
        accounts = self.generate_normal_accounts(num_accounts)
        txns, errors = self.generate_normal_transactions(accounts, num_transactions)
        return GeneratorResult(
            banks=[{"code": c} for c in BANK_CODES],
            accounts=accounts,
            transactions=txns,
            ground_truth=[],
            errors=errors,
        )
