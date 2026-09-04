import os
import tempfile
import unittest

from fraudlens.testing import use_isolated_data_dir

use_isolated_data_dir()

from fastapi.testclient import TestClient

from fraudlens.api.main import app
from fraudlens.core.cases.account_restriction import AccountRestrictionStore
from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.core.scoring.velocity_agent import VelocityAgent
from fraudlens.models.schemas import AgentScore, Transaction

_now = "2026-09-04T10:00:00+00:00"


def _txn(txn_id: str, account_id: str = "ACC-RESTRICT-1", timestamp: str = _now) -> Transaction:
    return Transaction(
        txn_id=txn_id, account_id=account_id, amount=5000.0, merchant_id="M1",
        merchant_category="electronics", device_id="D1", ip_address="1.2.3.4",
        timestamp=timestamp,
    )


class AccountRestrictionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        os.remove(self._tmp.name)
        self.addCleanup(lambda: os.path.exists(self._tmp.name) and os.remove(self._tmp.name))
        self.store = AccountRestrictionStore(path=self._tmp.name)

    def test_account_starts_unrestricted(self) -> None:
        self.assertFalse(self.store.is_restricted("ACC-1"))

    def test_restrict_then_is_restricted(self) -> None:
        self.store.restrict("ACC-1", "TXN-1", "CASE-TXN-1")
        self.assertTrue(self.store.is_restricted("ACC-1"))

    def test_restrict_is_idempotent(self) -> None:
        first = self.store.restrict("ACC-1", "TXN-1", "CASE-TXN-1")
        second = self.store.restrict("ACC-1", "TXN-2", "CASE-TXN-2")
        # Same restriction record — a later trigger doesn't overwrite the
        # original reason while the account is still actively restricted.
        self.assertEqual(first.applied_at, second.applied_at)
        self.assertEqual(second.reason_txn_id, "TXN-1")

    def test_release_clears_restriction(self) -> None:
        self.store.restrict("ACC-1", "TXN-1", "CASE-TXN-1")
        released = self.store.release("ACC-1", "A. Sharma")
        self.assertIsNotNone(released)
        self.assertFalse(self.store.is_restricted("ACC-1"))
        self.assertEqual(released.released_by, "A. Sharma")

    def test_release_of_unrestricted_account_is_a_noop(self) -> None:
        self.assertIsNone(self.store.release("ACC-NEVER-RESTRICTED", "A. Sharma"))

    def test_restrict_again_after_release_creates_a_new_active_restriction(self) -> None:
        self.store.restrict("ACC-1", "TXN-1", "CASE-TXN-1")
        self.store.release("ACC-1", "A. Sharma")
        self.assertFalse(self.store.is_restricted("ACC-1"))
        self.store.restrict("ACC-1", "TXN-2", "CASE-TXN-2")
        self.assertTrue(self.store.is_restricted("ACC-1"))
        self.assertEqual(self.store.get("ACC-1").reason_txn_id, "TXN-2")

    def test_persists_across_store_instances(self) -> None:
        self.store.restrict("ACC-1", "TXN-1", "CASE-TXN-1")
        reloaded = AccountRestrictionStore(path=self._tmp.name)
        self.assertTrue(reloaded.is_restricted("ACC-1"))


class VelocityAgentRestrictedModeTests(unittest.TestCase):
    """The actual mechanism: a restricted account trips the velocity
    agent's burst thresholds at a lower transaction count than normal."""

    def _history_with_two_recent_txns(self, account_id: str) -> list[Transaction]:
        return [
            _txn("TXN-HIST-1", account_id, "2026-09-04T09:50:00+00:00"),
            _txn("TXN-HIST-2", account_id, "2026-09-04T09:55:00+00:00"),
        ]

    def test_same_burst_scores_higher_when_account_is_restricted(self) -> None:
        account_id = "ACC-RESTRICTED"
        # Exactly 2 transactions in the last hour (2 history + this one = 3
        # total) — below the normal minor threshold's *trigger* point is
        # subtle, so compare the same fixture scored two ways instead of
        # reasoning about absolute thresholds.
        history = self._history_with_two_recent_txns(account_id)
        current = _txn("TXN-CURRENT", account_id)

        unrestricted_store = AccountRestrictionStore(path=tempfile.mktemp(suffix=".json"))
        unrestricted_agent = VelocityAgent(restriction_store=unrestricted_store)
        unrestricted_agent.set_transactions(history + [current])
        unrestricted_score = unrestricted_agent.score(current)

        restricted_store = AccountRestrictionStore(path=tempfile.mktemp(suffix=".json"))
        restricted_store.restrict(account_id, "TXN-TRIGGER", "CASE-TXN-TRIGGER")
        restricted_agent = VelocityAgent(restriction_store=restricted_store)
        restricted_agent.set_transactions(history + [current])
        restricted_score = restricted_agent.score(current)

        self.assertGreater(restricted_score.score, unrestricted_score.score)
        self.assertTrue(
            any("restriction" in r.lower() for r in restricted_score.reasons),
            restricted_score.reasons,
        )
        self.assertFalse(any("restriction" in r.lower() for r in unrestricted_score.reasons))

    def test_unrestricted_account_never_mentions_a_restriction(self) -> None:
        account_id = "ACC-NEVER-RESTRICTED"
        store = AccountRestrictionStore(path=tempfile.mktemp(suffix=".json"))
        agent = VelocityAgent(restriction_store=store)
        txn = _txn("TXN-SOLO", account_id)
        agent.set_transactions([txn])
        score = agent.score(txn)
        self.assertFalse(any("restriction" in r.lower() for r in score.reasons))


class _FakeAgent:
    def __init__(self, name: str, score: float, confidence: float = 0.95) -> None:
        self.name = name
        self._score = score
        self._confidence = confidence

    def score(self, txn: Transaction) -> AgentScore:
        return AgentScore(agent_name=self.name, score=self._score, confidence=self._confidence)


class CaseEngineAndVelocityIntegrationTests(unittest.TestCase):
    """Proves the cross-agent effect end to end at the engine level (no
    FastAPI): a case that trips auto-hold restricts its account, and the
    *next* transaction from that same account is scored differently by
    the real VelocityAgent because of it — not just a flag somewhere."""

    def setUp(self) -> None:
        self._cases_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._cases_tmp.close()
        self._restrictions_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._restrictions_tmp.close()
        os.remove(self._restrictions_tmp.name)
        for p in (self._cases_tmp.name, self._restrictions_tmp.name):
            self.addCleanup(lambda p=p: os.path.exists(p) and os.remove(p))

    def test_restriction_applied_after_hold_changes_next_transactions_velocity_score(self) -> None:
        account_id = "ACC-CROSS-AGENT"
        triggering_txn = _txn("TXN-TRIGGER", account_id, "2026-09-04T08:00:00+00:00")
        next_txn = _txn("TXN-NEXT", account_id, "2026-09-04T08:10:00+00:00")
        all_txns = [triggering_txn, next_txn]

        restriction_store = AccountRestrictionStore(path=self._restrictions_tmp.name)
        velocity_agent = VelocityAgent(restriction_store=restriction_store)
        velocity_agent.set_transactions(all_txns)

        # A single high-scoring fake agent is enough to clear the auto-hold
        # bar deterministically on its own (same pattern as
        # tests/test_autonomous_action.py) — it's the *only* agent CaseEngine
        # uses for the ensemble decision here, so the real VelocityAgent
        # doesn't dilute that weighted average. VelocityAgent's own real
        # score is exercised directly below instead, matching how
        # VelocityAgentRestrictedModeTests already verifies it.
        high_agent = _FakeAgent("rule_agent", 0.97, confidence=0.95)
        engine = CaseEngine(all_txns, agents=[high_agent], cases_path=self._cases_tmp.name)

        triggering_case = engine.analyze(triggering_txn.txn_id)
        self.assertEqual(triggering_case.system_action, "auto_held")
        self.assertFalse(restriction_store.is_restricted(account_id))  # engine alone doesn't restrict

        # This is what runtime.analyze() does in addition to engine.analyze() —
        # replicated directly here to test the mechanism without spinning up
        # the full FraudLensRuntime/build_runtime() (slow: fits ML models).
        restriction_store.restrict(account_id, triggering_case.txn_id, triggering_case.case_id)

        next_score = velocity_agent.score(next_txn)
        self.assertTrue(
            any("restriction" in r.lower() for r in next_score.reasons), next_score.reasons
        )

        # And releasing it removes the effect on a subsequent score.
        restriction_store.release(account_id, "A. Sharma")
        released_score = velocity_agent.score(next_txn)
        self.assertFalse(any("restriction" in r.lower() for r in released_score.reasons))


class AccountRestrictionApiTests(unittest.TestCase):
    """End-to-end against the real app and the real synthetic dataset —
    proves the full lifecycle through the actual HTTP surface, not just
    the internal mechanism."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.client.__enter__()
        # Find a real, currently-unrestricted account whose case genuinely
        # auto-holds under seed=42 — deterministic, not hardcoded to a
        # txn_id that could silently stop triggering if scoring changes.
        from fraudlens.api.state import state

        cls.txn_id = None
        for t in state.runtime.transactions:
            case = state.runtime.analyze(t.txn_id)
            if case.system_action == "auto_held":
                cls.txn_id = t.txn_id
                cls.account_id = case.transaction.account_id
                break
        assert cls.txn_id is not None, "no auto_held case found in the seed=42 dataset"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _login(self, username: str = "asharma") -> str:
        resp = self.client.post("/auth/login", json={"username": username, "password": "fraudlens123"})
        return resp.json()["access_token"]

    def test_auto_held_case_reports_account_restricted(self) -> None:
        case = self.client.get(f"/cases/{self.txn_id}").json()
        self.assertEqual(case["system_action"], "auto_held")
        self.assertTrue(case["account_restricted"])

    def test_reversing_the_decision_releases_the_restriction(self) -> None:
        # Confirm restricted first (may already be, from other tests
        # exercising the same deterministic case — that's fine).
        case = self.client.get(f"/cases/{self.txn_id}").json()
        self.assertTrue(case["account_restricted"])

        token = self._login("riyer")
        resp = self.client.post(
            "/decisions", json={"txn_id": self.txn_id, "decision": "review"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)

        released_case = self.client.get(f"/cases/{self.txn_id}").json()
        self.assertFalse(released_case["account_restricted"])
        self.assertIsNone(released_case["system_action"])

        events = self.client.get(f"/decisions/{self.txn_id}/audit").json()["events"]
        self.assertTrue(any(e["event_type"] == "account_restriction_applied" for e in events))
        released_events = [e for e in events if e["event_type"] == "account_restriction_released"]
        self.assertTrue(released_events)
        self.assertEqual(released_events[0]["actor"], "R. Iyer")


if __name__ == "__main__":
    unittest.main()
