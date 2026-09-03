import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from fraudlens.api.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.client.__enter__()  # trigger lifespan startup once for the whole test class

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_health(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_recent_transactions_returns_scored_feed(self) -> None:
        resp = self.client.get("/transactions/recent?limit=5")
        self.assertEqual(resp.status_code, 200)
        txns = resp.json()["transactions"]
        self.assertEqual(len(txns), 5)
        first = txns[0]
        self.assertIn("txn_id", first)
        self.assertIn("final_score", first)
        self.assertIn("decision", first)
        # account_id must be masked, never raw
        self.assertNotEqual(first["account_id"], "")
        self.assertIn("••", first["account_id"])

    def test_case_detail_masks_and_scores(self) -> None:
        txn_id = self.client.get("/transactions/recent?limit=1").json()["transactions"][0]["txn_id"]
        resp = self.client.get(f"/cases/{txn_id}")
        self.assertEqual(resp.status_code, 200)
        case = resp.json()
        self.assertEqual(case["txn_id"], txn_id)
        self.assertIn("••", case["transaction"]["account_id"])
        self.assertIsInstance(case["agent_scores"], list)
        self.assertGreaterEqual(len(case["agent_scores"]), 4)  # 5 once ml_agent always fires

    def test_case_detail_404_for_unknown_txn(self) -> None:
        resp = self.client.get("/cases/TXN-DOES-NOT-EXIST")
        self.assertEqual(resp.status_code, 404)

    def test_report_generation(self) -> None:
        txn_id = self.client.get("/transactions/recent?limit=1").json()["transactions"][0]["txn_id"]
        resp = self.client.get(f"/reports/{txn_id}")
        self.assertEqual(resp.status_code, 200)
        report = resp.json()
        self.assertEqual(report["txn_id"], txn_id)
        self.assertIn("Investigation Report", report["report_text"])

    def test_decision_submit_and_audit_round_trip(self) -> None:
        txn_id = self.client.get("/transactions/recent?limit=1").json()["transactions"][0]["txn_id"]
        self.client.get(f"/cases/{txn_id}")  # ensure a case exists

        resp = self.client.post("/decisions", json={
            "txn_id": txn_id, "decision": "review", "analyst": "test-analyst", "notes": "checking in",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["analyst"], "test-analyst")

        audit_resp = self.client.get(f"/decisions/{txn_id}/audit")
        self.assertEqual(audit_resp.status_code, 200)
        events = audit_resp.json()["events"]
        self.assertTrue(any(e["event_type"] == "analyst_decision" for e in events))

    def test_decision_rejects_invalid_value(self) -> None:
        txn_id = self.client.get("/transactions/recent?limit=1").json()["transactions"][0]["txn_id"]
        self.client.get(f"/cases/{txn_id}")
        resp = self.client.post("/decisions", json={"txn_id": txn_id, "decision": "not_a_real_decision"})
        self.assertEqual(resp.status_code, 400)

    def test_copilot_chat_without_api_key_returns_503_not_a_guess(self) -> None:
        # No GROQ_API_KEY in the test environment — the route must refuse
        # cleanly rather than silently answering without an LLM behind it.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GROQ_API_KEY", None)
            resp = self.client.post("/copilot/chat", json={"question": "why was this flagged?"})
        self.assertEqual(resp.status_code, 503)


if __name__ == "__main__":
    unittest.main()
