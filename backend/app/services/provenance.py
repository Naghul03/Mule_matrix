"""
Provenance Engine.

Implements two modes:
1. Conventional attribution — reconstructed from transaction records using FIFO or proportional allocation.
2. Simulated CBDC token lineage — parent-child records with strict amount conservation.

Mixed-fund accounting is handled via value lots per account.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Value lot: a unit of attributed value
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValueLot:
    provenance_id: str
    amount: Decimal
    origin_txn_ref: str
    label: str  # SUSPICIOUS, LEGITIMATE, CBDC_LINEAGE
    acquisition_ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────────────────────────────────────
# Account value store (mixed-fund accounting)
# ─────────────────────────────────────────────────────────────────────────────

class AccountValueStore:
    """
    Tracks value lots for one account.
    Enforces: no negative attributed balances, no over-allocation.
    """

    def __init__(self, account_ref: str):
        self.account_ref = account_ref
        self.lots: list[ValueLot] = []

    def add_lot(self, lot: ValueLot):
        self.lots.append(lot)

    def total_suspicious(self) -> Decimal:
        return sum(l.amount for l in self.lots if l.label == "SUSPICIOUS")

    def total_legitimate(self) -> Decimal:
        return sum(l.amount for l in self.lots if l.label == "LEGITIMATE")

    def total(self) -> Decimal:
        return sum(l.amount for l in self.lots)

    def allocate_fifo(self, outgoing_amount: Decimal) -> list[dict]:
        """
        FIFO allocation: consume lots from oldest first.
        Returns a list of {'provenance_id', 'amount', 'label'} dicts showing what was consumed.
        """
        if outgoing_amount > self.total():
            raise ValueError(
                f"Cannot allocate ₹{outgoing_amount} from account {self.account_ref}: "
                f"only ₹{self.total()} available."
            )

        remaining = outgoing_amount
        consumed = []
        new_lots = []

        for lot in self.lots:
            if remaining <= 0:
                new_lots.append(lot)
                continue
            take = min(lot.amount, remaining)
            consumed.append({
                "provenance_id": lot.provenance_id,
                "amount": take,
                "label": lot.label,
                "origin_txn_ref": lot.origin_txn_ref,
            })
            remaining -= take
            if lot.amount > take:
                # Partial lot — keep remainder
                new_lots.append(ValueLot(
                    provenance_id=lot.provenance_id,
                    amount=lot.amount - take,
                    origin_txn_ref=lot.origin_txn_ref,
                    label=lot.label,
                    acquisition_ts=lot.acquisition_ts,
                ))

        self.lots = new_lots
        return consumed

    def allocate_proportional(self, outgoing_amount: Decimal) -> list[dict]:
        """
        Proportional allocation: take from each lot in proportion to its share.
        """
        total = self.total()
        if total <= 0:
            return []
        if outgoing_amount > total:
            raise ValueError(
                f"Cannot allocate ₹{outgoing_amount} proportionally from account {self.account_ref}: "
                f"only ₹{total} available."
            )

        consumed = []
        for lot in self.lots:
            share = (lot.amount / total * outgoing_amount).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
            consumed.append({
                "provenance_id": lot.provenance_id,
                "amount": share,
                "label": lot.label,
                "origin_txn_ref": lot.origin_txn_ref,
            })
            lot.amount -= share

        self.lots = [l for l in self.lots if l.amount > 0]
        return consumed


# ─────────────────────────────────────────────────────────────────────────────
# CBDC Lineage record (in-memory, later persisted)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CBDCLineageNode:
    provenance_id: str
    parent_id: str | None
    initial_amount: Decimal
    remaining_amount: Decimal
    current_holder: str
    origin_txn_ref: str
    children: list[str] = field(default_factory=list)
    transfers: list[dict] = field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, SPLIT, TRANSFERRED, DEPLETED
    notes: str = ""

    def split(self, child_amounts: list[Decimal]) -> list["CBDCLineageNode"]:
        """
        Split this node into children. Enforces amount conservation.
        child_amounts must sum ≤ self.remaining_amount.
        """
        import uuid
        total_child = sum(child_amounts)
        if total_child > self.remaining_amount:
            raise ValueError(
                f"Split amounts {total_child} exceed remaining {self.remaining_amount} "
                f"for provenance {self.provenance_id}."
            )

        children = []
        for amt in child_amounts:
            child = CBDCLineageNode(
                provenance_id=str(uuid.uuid4()),
                parent_id=self.provenance_id,
                initial_amount=amt,
                remaining_amount=amt,
                current_holder=self.current_holder,
                origin_txn_ref=self.origin_txn_ref,
            )
            self.children.append(child.provenance_id)
            children.append(child)

        retained = self.remaining_amount - total_child
        self.remaining_amount = retained
        self.status = "SPLIT"
        return children

    def transfer(self, txn_ref: str, new_holder: str, amount: Decimal) -> "CBDCLineageNode":
        """Transfer a portion to a new holder. Returns a child node."""
        import uuid
        if amount > self.remaining_amount:
            raise ValueError(
                f"Cannot transfer ₹{amount}: only ₹{self.remaining_amount} remaining "
                f"in provenance {self.provenance_id}."
            )
        child = CBDCLineageNode(
            provenance_id=str(uuid.uuid4()),
            parent_id=self.provenance_id,
            initial_amount=amount,
            remaining_amount=amount,
            current_holder=new_holder,
            origin_txn_ref=self.origin_txn_ref,
        )
        self.remaining_amount -= amount
        if self.remaining_amount <= 0:
            self.status = "DEPLETED"
        else:
            self.status = "TRANSFERRED"
        self.transfers.append({
            "txn_ref": txn_ref,
            "to": new_holder,
            "amount": float(amount),
            "child_provenance_id": child.provenance_id,
        })
        self.children.append(child.provenance_id)
        return child


# ─────────────────────────────────────────────────────────────────────────────
# Provenance engine
# ─────────────────────────────────────────────────────────────────────────────

class ProvenanceEngine:

    def __init__(self, allocation_method: str = "FIFO"):
        self.allocation_method = allocation_method
        self.account_stores: dict[str, AccountValueStore] = {}
        self.cbdc_nodes: dict[str, CBDCLineageNode] = {}

    def _get_store(self, account_ref: str) -> AccountValueStore:
        if account_ref not in self.account_stores:
            self.account_stores[account_ref] = AccountValueStore(account_ref)
        return self.account_stores[account_ref]

    # ── Conventional attribution ───────────────────────────────────────────

    def record_suspicious_inflow(
        self, account_ref: str, provenance_id: str,
        amount: Decimal, origin_txn_ref: str,
    ):
        """Record a suspicious incoming value lot for mixed-fund tracking."""
        lot = ValueLot(
            provenance_id=provenance_id,
            amount=amount,
            origin_txn_ref=origin_txn_ref,
            label="SUSPICIOUS",
        )
        self._get_store(account_ref).add_lot(lot)

    def record_legitimate_inflow(
        self, account_ref: str, amount: Decimal, origin_txn_ref: str,
    ):
        """Record a legitimate incoming value lot."""
        lot = ValueLot(
            provenance_id=f"LEGIT_{origin_txn_ref}",
            amount=amount,
            origin_txn_ref=origin_txn_ref,
            label="LEGITIMATE",
        )
        self._get_store(account_ref).add_lot(lot)

    def allocate_outflow(
        self, account_ref: str, amount: Decimal
    ) -> list[dict]:
        """Allocate outgoing value using the configured method."""
        store = self._get_store(account_ref)
        if self.allocation_method == "FIFO":
            return store.allocate_fifo(amount)
        return store.allocate_proportional(amount)

    def get_suspicious_balance(self, account_ref: str) -> Decimal:
        return self._get_store(account_ref).total_suspicious()

    def get_full_balance(self, account_ref: str) -> Decimal:
        return self._get_store(account_ref).total()

    # ── CBDC lineage ───────────────────────────────────────────────────────

    def create_cbdc_root(
        self, provenance_id: str, origin_txn_ref: str,
        initial_amount: Decimal, holder: str,
    ) -> CBDCLineageNode:
        node = CBDCLineageNode(
            provenance_id=provenance_id,
            parent_id=None,
            initial_amount=initial_amount,
            remaining_amount=initial_amount,
            current_holder=holder,
            origin_txn_ref=origin_txn_ref,
        )
        self.cbdc_nodes[provenance_id] = node
        return node

    def split_cbdc(
        self, parent_id: str, child_amounts: list[Decimal]
    ) -> list[CBDCLineageNode]:
        parent = self.cbdc_nodes.get(parent_id)
        if parent is None:
            raise ValueError(f"Provenance node {parent_id} not found.")
        children = parent.split(child_amounts)
        for child in children:
            self.cbdc_nodes[child.provenance_id] = child
        return children

    def transfer_cbdc(
        self, parent_id: str, txn_ref: str, new_holder: str, amount: Decimal
    ) -> CBDCLineageNode:
        parent = self.cbdc_nodes.get(parent_id)
        if parent is None:
            raise ValueError(f"Provenance node {parent_id} not found.")
        child = parent.transfer(txn_ref, new_holder, amount)
        self.cbdc_nodes[child.provenance_id] = child
        return child

    def get_lineage_tree(self, root_id: str) -> dict:
        """Return the full lineage tree rooted at root_id."""
        node = self.cbdc_nodes.get(root_id)
        if node is None:
            return {}
        return self._build_tree(node)

    def _build_tree(self, node: CBDCLineageNode) -> dict:
        return {
            "provenance_id": node.provenance_id,
            "parent_id": node.parent_id,
            "initial_amount": float(node.initial_amount),
            "remaining_amount": float(node.remaining_amount),
            "current_holder": node.current_holder,
            "status": node.status,
            "children": [self._build_tree(self.cbdc_nodes[cid]) for cid in node.children if cid in self.cbdc_nodes],
        }

    def validate_conservation(self, root_id: str) -> dict:
        """Validate that no child exceeds its parent's initial amount (conservation check)."""
        root = self.cbdc_nodes.get(root_id)
        if root is None:
            return {"valid": False, "error": "Root not found"}
        errors = []
        self._check_conservation(root, errors)
        return {"valid": len(errors) == 0, "errors": errors}

    def _check_conservation(self, node: CBDCLineageNode, errors: list):
        total_child_initial = sum(
            self.cbdc_nodes[cid].initial_amount
            for cid in node.children
            if cid in self.cbdc_nodes
        )
        if total_child_initial > node.initial_amount:
            errors.append(
                f"Node {node.provenance_id}: children total {total_child_initial} "
                f"exceeds initial {node.initial_amount}."
            )
        for cid in node.children:
            if cid in self.cbdc_nodes:
                self._check_conservation(self.cbdc_nodes[cid], errors)
