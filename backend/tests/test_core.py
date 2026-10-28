"""
Pytest tests for Mule Matrix backend.

Covers:
- Normalisation (all four adapters)
- Provenance engine
- Graph engine
- Scenario generation
- Behavioural detection
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta


# ─────────────────────────────────────────────────────────────────────────────
# Adapter / Normalisation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBankAAdapter:
    def _adapter(self):
        from app.adapters.bank_a import BankAAdapter
        return BankAAdapter(bank_id="test-bank-a")

    def test_valid_record(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "txn_id": "TXN001",
            "sender": "A100",
            "receiver": "B200",
            "amount": "50000.00",
            "timestamp": "2024-01-15T10:30:00Z",
            "status": "SUCCESS",
        })
        assert result.status == "ACCEPTED"
        assert result.canonical is not None
        assert result.canonical.amount == Decimal("50000.00")
        assert result.canonical.sender_account_ref == "A100"
        assert result.canonical.receiver_account_ref == "B200"
        assert result.canonical.currency == "INR"
        assert result.canonical.timestamp_utc.tzinfo is not None

    def test_missing_sender(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "txn_id": "TXN002",
            "receiver": "B200",
            "amount": "100",
            "timestamp": "2024-01-15T10:30:00Z",
        })
        assert result.status == "REJECTED"
        assert any("sender" in e for e in result.errors)

    def test_negative_amount(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "txn_id": "TXN003",
            "sender": "A100",
            "receiver": "B200",
            "amount": "-500",
            "timestamp": "2024-01-15T10:30:00Z",
        })
        assert result.status == "REJECTED"

    def test_source_reference_preserved(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "txn_id": "ORIGINAL_REF_XYZ",
            "sender": "A1",
            "receiver": "B1",
            "amount": "1000",
            "timestamp": "2024-01-15T10:30:00Z",
        })
        assert result.canonical.source_reference == "ORIGINAL_REF_XYZ"


class TestBankBAdapter:
    def _adapter(self):
        from app.adapters.bank_b import BankBAdapter
        return BankBAdapter(bank_id="test-bank-b")

    def test_valid_record(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "reference": "REF_B001",
            "debit_acct": "DEBIT100",
            "credit_acct": "CREDIT200",
            "txn_amount": "75000.50",
            "txn_date": "2024-02-10 14:30:00",
            "txn_status": "SETTLED",
        })
        assert result.status == "ACCEPTED"
        assert result.canonical.amount == Decimal("75000.50")
        assert result.canonical.sender_account_ref == "DEBIT100"
        assert result.canonical.receiver_account_ref == "CREDIT200"
        # Timestamp should be in UTC (converted from IST)
        assert result.canonical.timestamp_utc.tzinfo is not None

    def test_missing_reference(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "debit_acct": "D1",
            "credit_acct": "C1",
            "txn_amount": "100",
            "txn_date": "2024-01-01 10:00:00",
        })
        assert result.status == "REJECTED"


class TestBankCAdapter:
    def _adapter(self):
        from app.adapters.bank_c import BankCAdapter
        return BankCAdapter(bank_id="test-bank-c")

    def test_paise_conversion(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "id": "C001",
            "from_account": "F100",
            "to_account": "T200",
            "value_paise": 500000,  # ₹5,000
            "event_time": 1705300200,
            "event_status": "SUCCESS",
        })
        assert result.status == "ACCEPTED"
        assert result.canonical.amount == Decimal("5000.00")

    def test_zero_paise_warning(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "id": "C002",
            "from_account": "F100",
            "to_account": "T200",
            "value_paise": 0,
            "event_time": 1705300200,
        })
        # Zero paise should produce a warning not a rejection
        assert result.status in ("WARNING", "ACCEPTED")
        assert any("zero" in w.lower() for w in result.warnings)

    def test_negative_paise_rejected(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "id": "C003",
            "from_account": "F100",
            "to_account": "T200",
            "value_paise": -1000,
            "event_time": 1705300200,
        })
        assert result.status == "REJECTED"

    def test_unix_timestamp_parsed(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "id": "C004",
            "from_account": "F1",
            "to_account": "T1",
            "value_paise": 10000,
            "event_time": 0,  # epoch
        })
        assert result.canonical is not None
        assert result.canonical.timestamp_utc.year == 1970


class TestBankDAdapter:
    def _adapter(self):
        from app.adapters.bank_d import BankDAdapter
        return BankDAdapter(bank_id="test-bank-d")

    def test_valid_inr(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "msg_id": "D001",
            "ordering_account": "ORD100",
            "beneficiary_account": "BEN200",
            "instructed_amount": "200000",
            "instructed_currency": "INR",
            "value_date": "20240115",
            "msg_status": "ACSC",
        })
        assert result.status == "ACCEPTED"
        assert result.canonical.amount == Decimal("200000")

    def test_usd_conversion(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "msg_id": "D002",
            "ordering_account": "ORD100",
            "beneficiary_account": "BEN200",
            "instructed_amount": "1000",
            "instructed_currency": "USD",
            "value_date": "20240115",
            "msg_status": "ACSC",
        })
        assert result.status in ("ACCEPTED", "WARNING")
        assert result.canonical.amount == Decimal("1000") * Decimal("83.5")
        assert any("Converted" in w for w in result.warnings)

    def test_yyyymmdd_date_parsing(self):
        adapter = self._adapter()
        result = adapter.normalise({
            "msg_id": "D003",
            "ordering_account": "ORD1",
            "beneficiary_account": "BEN1",
            "instructed_amount": "5000",
            "instructed_currency": "INR",
            "value_date": "20240315",
            "msg_status": "ACSC",
        })
        assert result.canonical.timestamp_utc.year == 2024
        assert result.canonical.timestamp_utc.month == 3
        assert result.canonical.timestamp_utc.day == 15


# ─────────────────────────────────────────────────────────────────────────────
# Provenance Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProvenanceEngine:
    def _engine(self, method="FIFO"):
        from app.services.provenance import ProvenanceEngine
        return ProvenanceEngine(allocation_method=method)

    def test_fifo_allocation(self):
        eng = self._engine("FIFO")
        eng.record_suspicious_inflow("ACC1", "PROV1", Decimal("200000"), "TXN_ORIG")
        eng.record_legitimate_inflow("ACC1", Decimal("100000"), "LEGIT1")

        # FIFO: should consume suspicious lot first
        consumed = eng.allocate_outflow("ACC1", Decimal("150000"))
        assert sum(c["amount"] for c in consumed) == Decimal("150000")
        # First consumed lot should be suspicious
        assert consumed[0]["label"] == "SUSPICIOUS"

    def test_no_over_allocation(self):
        eng = self._engine()
        eng.record_suspicious_inflow("ACC2", "PROV2", Decimal("50000"), "TXN1")
        with pytest.raises(ValueError):
            eng.allocate_outflow("ACC2", Decimal("100000"))

    def test_remaining_balance_correct(self):
        eng = self._engine()
        eng.record_suspicious_inflow("ACC3", "PROV3", Decimal("100000"), "TXN1")
        eng.allocate_outflow("ACC3", Decimal("40000"))
        assert eng.get_suspicious_balance("ACC3") == Decimal("60000")

    def test_proportional_allocation(self):
        eng = self._engine("PROPORTIONAL")
        eng.record_suspicious_inflow("ACC4", "PROV4", Decimal("100000"), "TXN1")
        eng.record_legitimate_inflow("ACC4", Decimal("100000"), "LEGIT1")
        consumed = eng.allocate_outflow("ACC4", Decimal("100000"))
        total = sum(c["amount"] for c in consumed)
        # Total consumed must equal outgoing (within rounding)
        assert abs(total - Decimal("100000")) < Decimal("1")

    def test_cbdc_split_conservation(self):
        from app.services.provenance import ProvenanceEngine
        eng = ProvenanceEngine()
        root = eng.create_cbdc_root("ROOT1", "ORIG_TXN", Decimal("500000"), "ORIGIN_ACC")
        children = eng.split_cbdc("ROOT1", [Decimal("200000"), Decimal("300000")])
        assert len(children) == 2
        assert children[0].initial_amount == Decimal("200000")
        assert children[1].initial_amount == Decimal("300000")
        # Conservation check
        validation = eng.validate_conservation("ROOT1")
        assert validation["valid"]

    def test_cbdc_split_exceeds_parent(self):
        from app.services.provenance import ProvenanceEngine
        eng = ProvenanceEngine()
        eng.create_cbdc_root("ROOT2", "ORIG", Decimal("100000"), "ACC")
        with pytest.raises(ValueError):
            eng.split_cbdc("ROOT2", [Decimal("80000"), Decimal("80000")])

    def test_cbdc_lineage_tree(self):
        from app.services.provenance import ProvenanceEngine
        eng = ProvenanceEngine()
        eng.create_cbdc_root("ROOT3", "ORIG", Decimal("500000"), "H1")
        children = eng.split_cbdc("ROOT3", [Decimal("200000"), Decimal("300000")])
        p1_id = children[0].provenance_id
        eng.split_cbdc(p1_id, [Decimal("50000"), Decimal("150000")])
        tree = eng.get_lineage_tree("ROOT3")
        assert len(tree["children"]) == 2
        p1_tree = tree["children"][0]
        assert len(p1_tree["children"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Graph Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphEngine:
    def _sample_txns(self):
        base_ts = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        return [
            {
                "id": "T1", "transaction_ref": "T1",
                "sender_account_ref": "VICTIM", "receiver_account_ref": "MULE_A",
                "amount": 400000, "currency": "INR",
                "timestamp_utc": (base_ts + timedelta(days=2)).isoformat(),
                "status": "COMPLETED", "is_suspicious": False, "risk_score": 0,
                "source_bank_id": "BANK_A", "destination_bank_id": "BANK_B",
            },
            {
                "id": "T2", "transaction_ref": "T2",
                "sender_account_ref": "MULE_A", "receiver_account_ref": "MULE_B",
                "amount": 180000, "currency": "INR",
                "timestamp_utc": (base_ts + timedelta(days=2, hours=2)).isoformat(),
                "status": "COMPLETED", "is_suspicious": False, "risk_score": 0,
                "source_bank_id": "BANK_B", "destination_bank_id": "BANK_C",
            },
            {
                "id": "T3", "transaction_ref": "T3",
                "sender_account_ref": "MULE_A", "receiver_account_ref": "MULE_C",
                "amount": 150000, "currency": "INR",
                "timestamp_utc": (base_ts + timedelta(days=2, hours=3)).isoformat(),
                "status": "COMPLETED", "is_suspicious": False, "risk_score": 0,
                "source_bank_id": "BANK_B", "destination_bank_id": "BANK_C",
            },
            {
                "id": "T4", "transaction_ref": "T4",
                "sender_account_ref": "MULE_B", "receiver_account_ref": "BENEFICIARY",
                "amount": 175000, "currency": "INR",
                "timestamp_utc": (base_ts + timedelta(days=2, hours=15)).isoformat(),
                "status": "COMPLETED", "is_suspicious": False, "risk_score": 0,
                "source_bank_id": "BANK_C", "destination_bank_id": "BANK_D",
            },
        ]

    def test_forward_trace(self):
        from app.services.graph_engine import build_graph, forward_trace
        txns = self._sample_txns()
        G = build_graph(txns)
        result = forward_trace(G, "VICTIM", max_depth=4)
        assert "MULE_A" in result["nodes"]
        assert "MULE_B" in result["nodes"]
        assert "BENEFICIARY" in result["nodes"]

    def test_backward_trace(self):
        from app.services.graph_engine import build_graph, backward_trace
        txns = self._sample_txns()
        G = build_graph(txns)
        result = backward_trace(G, "BENEFICIARY", max_depth=4)
        assert "MULE_B" in result["nodes"]
        assert "MULE_A" in result["nodes"]
        assert "VICTIM" in result["nodes"]
        # All edges must preserve actual direction
        for edge in result["edges"]:
            assert "from" in edge
            assert "to" in edge

    def test_edge_direction_preserved_in_backward(self):
        from app.services.graph_engine import build_graph, backward_trace
        txns = self._sample_txns()
        G = build_graph(txns)
        result = backward_trace(G, "MULE_A", max_depth=2)
        # VICTIM→MULE_A edge must be represented as from=VICTIM, to=MULE_A
        victim_edge = next(
            (e for e in result["edges"] if e["from"] == "VICTIM" and e["to"] == "MULE_A"),
            None
        )
        assert victim_edge is not None, "VICTIM→MULE_A edge direction should be preserved in backward trace"

    def test_fan_out_detected(self):
        from app.services.graph_engine import build_graph, detect_fan_out
        txns = self._sample_txns()
        G = build_graph(txns)
        fan_out = detect_fan_out(G, threshold=2)  # MULE_A sends to 2 destinations
        accounts = [r["account"] for r in fan_out]
        assert "MULE_A" in accounts

    def test_fan_in_detected(self):
        from app.services.graph_engine import build_graph, detect_fan_in
        # Add another transaction to BENEFICIARY
        txns = self._sample_txns() + [{
            "id": "T5", "transaction_ref": "T5",
            "sender_account_ref": "MULE_C", "receiver_account_ref": "BENEFICIARY",
            "amount": 140000, "currency": "INR",
            "timestamp_utc": datetime(2024, 1, 12, 15, 0, tzinfo=timezone.utc).isoformat(),
            "status": "COMPLETED", "is_suspicious": False, "risk_score": 0,
            "source_bank_id": "BANK_C", "destination_bank_id": "BANK_D",
        }]
        from app.services.graph_engine import build_graph, detect_fan_in
        G = build_graph(txns)
        fan_in = detect_fan_in(G, threshold=2)
        accounts = [r["account"] for r in fan_in]
        assert "BENEFICIARY" in accounts

    def test_cycle_detection(self):
        from app.services.graph_engine import build_graph, detect_cycles
        txns = self._sample_txns() + [{
            "id": "T6", "transaction_ref": "T6",
            "sender_account_ref": "BENEFICIARY", "receiver_account_ref": "MULE_A",
            "amount": 50000, "currency": "INR",
            "timestamp_utc": datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc).isoformat(),
            "status": "COMPLETED", "is_suspicious": False, "risk_score": 0,
            "source_bank_id": "BANK_D", "destination_bank_id": "BANK_B",
        }]
        G = build_graph(txns)
        cycles = detect_cycles(G)
        assert len(cycles) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3 — Temporal correctness tests
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario3Temporal:
    def _gen(self):
        from app.services.generator import SyntheticGenerator
        return SyntheticGenerator(seed=42, timespan_days=30)

    def test_pre_positioned_transfers_predate_victim(self):
        gen = self._gen()
        result = gen.generate_scenario_3()

        # Find ground-truth labels
        victim_ref = next(gt["entity_id"] for gt in result.ground_truth if gt["label"] == "VICTIM")
        mule_b_ref = next(gt["entity_id"] for gt in result.ground_truth if "Mule B" in gt.get("notes", "") or gt["label"] == "MULE")
        # Find the victim→A transaction
        victim_txn = next(
            t for t in result.transactions
            if t.sender_ref == victim_ref and t.scenario_label == "VICTIM_TO_MULE"
        )
        # Find B→D transactions
        pre_positioned = [
            t for t in result.transactions if t.scenario_label == "PRE_POSITION"
        ]
        assert len(pre_positioned) == 2
        for pp in pre_positioned:
            assert pp.timestamp_utc < victim_txn.timestamp_utc, (
                "Pre-positioned transfers must occur BEFORE the victim transaction"
            )

    def test_replenishment_follows_victim_transaction(self):
        gen = self._gen()
        result = gen.generate_scenario_3()

        victim_txn = next(
            t for t in result.transactions if t.scenario_label == "VICTIM_TO_MULE"
        )
        replenishments = [t for t in result.transactions if t.scenario_label == "REPLENISHMENT"]
        assert len(replenishments) == 2
        for r in replenishments:
            assert r.timestamp_utc > victim_txn.timestamp_utc, (
                "Replenishments (A→B, A→C) must occur AFTER the victim transaction"
            )

    def test_no_negative_balances(self):
        gen = self._gen()
        result = gen.generate_scenario_3()
        # All accounts should have non-negative balance after all transactions
        for acc in result.accounts:
            assert acc.balance >= 0, f"Account {acc.account_ref} has negative balance {acc.balance}"


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4 — Below-threshold screening
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario4BelowThreshold:
    def _gen(self):
        from app.services.generator import SyntheticGenerator
        return SyntheticGenerator(seed=42, timespan_days=30)

    def test_fragment_amounts_below_threshold(self):
        gen = self._gen()
        result = gen.generate_scenario_4()
        HIGH_VALUE_THRESHOLD = Decimal("1000000")
        fragments = [t for t in result.transactions if t.scenario_label == "FRAGMENT"]
        assert len(fragments) == 8
        for f in fragments:
            assert f.amount < HIGH_VALUE_THRESHOLD, (
                f"Fragment {f.id} amount {f.amount} should be below threshold {HIGH_VALUE_THRESHOLD}"
            )

    def test_fragment_amounts_sum_to_victim_loss(self):
        gen = self._gen()
        result = gen.generate_scenario_4()
        fragments = [t for t in result.transactions if t.scenario_label == "FRAGMENT"]
        total = sum(t.amount for t in fragments)
        expected = Decimal("120000") * 8  # ₹9.6L
        assert total == expected


# ─────────────────────────────────────────────────────────────────────────────
# Behavioural Detection Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBehaviouralDetection:
    def test_risk_fusion_high_pass_through(self):
        from app.services.detection import fuse_risk
        result = fuse_risk({
            "dwell_time_hours": 0.5,
            "pass_through_ratio": 92.0,
            "count_in_window": 3,
        })
        assert result["risk_score"] >= 40
        assert result["severity"] in ("MEDIUM", "HIGH", "CRITICAL")
        assert len(result["evidence"]) > 0

    def test_risk_fusion_low_risk(self):
        from app.services.detection import fuse_risk
        result = fuse_risk({
            "dwell_time_hours": 48.0,
            "pass_through_ratio": 5.0,
        })
        assert result["risk_score"] < 30
        assert result["severity"] == "LOW"

    def test_dwell_time_rapid_passthrough(self):
        from app.services.detection import compute_dwell_time
        base = datetime(2024, 1, 10, 9, 0, 0, tzinfo=timezone.utc)
        incoming = [{"id": "I1", "timestamp_utc": base.isoformat(), "amount": 100000}]
        outgoing = [{"id": "O1", "timestamp_utc": (base + timedelta(minutes=10)).isoformat(), "amount": 95000}]
        result = compute_dwell_time(incoming, outgoing)
        assert result["dwell_time_hours"] is not None
        assert result["dwell_time_hours"] < 1.0

    def test_pass_through_ratio_calculation(self):
        from app.services.detection import compute_pass_through_ratio
        incoming = [{"id": "I1", "amount": 100000}]
        outgoing = [{"id": "O1", "amount": 90000}]
        result = compute_pass_through_ratio(incoming, outgoing)
        assert result["pass_through_ratio"] == 90.0
