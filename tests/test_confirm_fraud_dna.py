"""CaseEngine.confirm_fraud_dna(): the library only grows from analyst-
confirmed cases, not raw engine detections — and once it grows, a *new*
ring under different accounts should match against what was just learned.
"""

import os
import tempfile
import unittest

from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.core.dna.store import FraudDNAStore
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.models.schemas import Transaction


def _ring(prefix: str, device: str, ip: str, amount_base: float) -> list[Transaction]:
    txns = []
    for i in range(5):
        txns.append(Transaction(
            txn_id=f"{prefix}-T{i}", account_id=f"{prefix}-A{i}", amount=amount_base + i,
            merchant_id="M1", merchant_category="money_transfer", device_id=device,
            ip_address=ip, timestamp=f"2026-09-01T{10+i}:00:00+00:00",
        ))
    return txns


class ConfirmFraudDnaTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cases_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._cases_tmp.close()
        self._dna_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._dna_tmp.close()
        os.remove(self._dna_tmp.name)
        self.addCleanup(lambda: os.path.exists(self._cases_tmp.name) and os.remove(self._cases_tmp.name))
        self.addCleanup(lambda: os.path.exists(self._dna_tmp.name) and os.remove(self._dna_tmp.name))

    def _engine(self, transactions: list[Transaction]) -> CaseEngine:
        graph_agent = GraphAgent()
        graph_agent.build_index(transactions)
        return CaseEngine(
            transactions, agents=[graph_agent], cases_path=self._cases_tmp.name,
            dna_store=FraudDNAStore(path=self._dna_tmp.name),
        )

    def test_confirming_a_ring_adds_it_to_the_library(self) -> None:
        ring = _ring("NOVEL", "D_NOVEL", "IP_NOVEL", amount_base=777.0)
        engine = self._engine(ring)
        engine.analyze(ring[0].txn_id)

        profile = engine.confirm_fraud_dna(ring[0].txn_id)

        self.assertIsNotNone(profile)
        self.assertTrue(profile.ring_id.startswith("CONFIRMED-"))

    def test_confirming_twice_is_idempotent(self) -> None:
        ring = _ring("DUP", "D_DUP", "IP_DUP", amount_base=500.0)
        engine = self._engine(ring)
        engine.analyze(ring[0].txn_id)

        first = engine.confirm_fraud_dna(ring[0].txn_id)
        second = engine.confirm_fraud_dna(ring[0].txn_id)

        self.assertEqual(first.ring_id, second.ring_id)

    def test_transaction_with_no_ring_cannot_be_confirmed(self) -> None:
        lone = Transaction(
            txn_id="LONE-1", account_id="LONE-A", amount=50.0, merchant_id="M1",
            merchant_category="groceries", device_id="D_LONE", ip_address="IP_LONE",
            timestamp="2026-09-01T10:00:00+00:00",
        )
        engine = self._engine([lone])
        engine.analyze(lone.txn_id)

        self.assertIsNone(engine.confirm_fraud_dna(lone.txn_id))

    def test_a_new_ring_matches_a_previously_confirmed_pattern(self) -> None:
        """The actual point: confirming a ring today should help catch the
        *next* one, under completely different accounts/devices."""
        first_ring = _ring("FIRST", "D_FIRST", "IP_FIRST", amount_base=900.0)
        engine = self._engine(first_ring)
        engine.analyze(first_ring[0].txn_id)
        engine.confirm_fraud_dna(first_ring[0].txn_id)

        # A second, later ring with the same shape (size, amount range,
        # velocity) but entirely different accounts/devices/IPs.
        second_ring = _ring("SECOND", "D_SECOND", "IP_SECOND", amount_base=910.0)
        engine2 = self._engine(first_ring + second_ring)
        # Re-confirm the first ring on the new engine instance (library is
        # shared via the same dna_store path, but this engine's graph
        # includes both rings, so re-run analyze to rebuild its own cases).
        engine2.analyze(first_ring[0].txn_id)
        engine2.confirm_fraud_dna(first_ring[0].txn_id)

        case = engine2.analyze(second_ring[0].txn_id)

        self.assertIsNotNone(case.fraud_dna_match)


if __name__ == "__main__":
    unittest.main()
