import os
import unittest
from unittest.mock import patch

from fraudlens.testing import use_isolated_data_dir

use_isolated_data_dir()

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

    def test_report_pdf_download_for_normal_transaction(self) -> None:
        # Deterministic normal-pattern transaction — no graph/Fraud DNA evidence.
        txn_id = "TXN-E3A14F5D6ED5855D"
        resp = self.client.get(f"/reports/{txn_id}/pdf")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertIn("attachment", resp.headers["content-disposition"])
        self.assertIn(f"report-{txn_id}.pdf", resp.headers["content-disposition"])
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_report_pdf_download_for_ring_transaction_with_graph_and_dna(self) -> None:
        # Deterministic ring-pattern transaction — has graph evidence and,
        # via the seeded Fraud DNA library, a match too.
        txn_id = "TXN-AF493E2FCD007CAD"
        resp = self.client.get(f"/reports/{txn_id}/pdf")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_report_pdf_404_for_unknown_txn(self) -> None:
        resp = self.client.get("/reports/TXN-DOES-NOT-EXIST/pdf")
        self.assertEqual(resp.status_code, 404)

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

    def test_case_graph_returns_real_masked_ring_for_a_ring_transaction(self) -> None:
        # Deterministic under the fixed seed=42 synthetic dataset — a
        # known fraud_ring-pattern transaction.
        txn_id = "TXN-AF493E2FCD007CAD"
        resp = self.client.get(f"/cases/{txn_id}/graph")
        self.assertEqual(resp.status_code, 200)
        graph = resp.json()["graph"]
        self.assertIsNotNone(graph)
        self.assertGreaterEqual(graph["ring_size"], 2)
        account_nodes = [n for n in graph["nodes"] if n["node_type"] == "account"]
        self.assertEqual(len(account_nodes), graph["ring_size"])
        self.assertGreater(len(graph["edges"]), 0)

        # Every account/device/merchant label must be masked; every ip
        # label must be masked; no node id may look like a raw identifier.
        for node in graph["nodes"]:
            if node["node_type"] in ("account", "device", "merchant"):
                self.assertIn("••", node["label"])
            if node["node_type"] == "ip":
                self.assertIn("••", node["label"])

        self.assertIsNotNone(graph["flagged_node_id"])
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn(graph["flagged_node_id"], node_ids)
        for edge in graph["edges"]:
            self.assertIn(edge["source"], node_ids)
            self.assertIn(edge["target"], node_ids)

    def test_case_graph_is_null_for_a_non_ring_transaction(self) -> None:
        txn_id = "TXN-E3A14F5D6ED5855D"  # deterministic normal-pattern transaction
        resp = self.client.get(f"/cases/{txn_id}/graph")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["graph"])

    def test_case_graph_404_for_unknown_txn(self) -> None:
        resp = self.client.get("/cases/TXN-DOES-NOT-EXIST/graph")
        self.assertEqual(resp.status_code, 404)

    def test_copilot_chat_without_api_key_returns_503_not_a_guess(self) -> None:
        # No GROQ_API_KEY in the test environment — the route must refuse
        # cleanly rather than silently answering without an LLM behind it.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GROQ_API_KEY", None)
            resp = self.client.post("/copilot/chat", json={"question": "why was this flagged?"})
        self.assertEqual(resp.status_code, 503)

    def test_copilot_chat_live_call_failure_returns_clean_error_not_500(self) -> None:
        # A KEY IS SET (constructor succeeds), but the actual live call to
        # Groq fails (invalid key, bad model, network error — anything).
        # This previously escaped the route's try/except entirely (it only
        # wrapped the constructor) and surfaced as an opaque, undebuggable
        # 500. Real regression test for the exact bug hit during live
        # testing, not a hypothetical.
        import httpx

        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-key-for-this-test"}):
            with patch("fraudlens.core.copilot.agent.httpx.post") as mock_post:
                mock_post.side_effect = httpx.ConnectError("simulated network failure")
                resp = self.client.post(
                    "/copilot/chat", json={"question": "why was this flagged?", "txn_id": "TXN-0001"}
                )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Copilot's LLM call failed", resp.json()["detail"])

    def test_false_positive_never_confirms_fraud_dna(self) -> None:
        # CRITICAL correctness constraint: a confirmed false positive must
        # never teach the Fraud DNA library what fraud looks like. Uses the
        # known deterministic ring/block_and_report transaction (see the
        # graph tests above) — if the guard in api/routes/decisions.py ever
        # regressed, this exact submission would add a CONFIRMED-* profile.
        txn_id = "TXN-AF493E2FCD007CAD"
        self.client.get(f"/cases/{txn_id}")

        before_ring_ids = {p["ring_id"] for p in self.client.get("/dna/patterns").json()["patterns"]}

        resp = self.client.post("/decisions", json={
            "txn_id": txn_id, "decision": "clear", "analyst": "fp-test-analyst",
            "notes": "Investigated the ring — legitimate shared household device.",
            "is_false_positive": True,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["is_false_positive"])
        self.assertEqual(resp.json()["decision"], "clear")

        after_ring_ids = {p["ring_id"] for p in self.client.get("/dna/patterns").json()["patterns"]}
        self.assertEqual(before_ring_ids, after_ring_ids)
        self.assertFalse(any(rid.startswith("CONFIRMED-") for rid in after_ring_ids))

    def test_decision_rejects_false_positive_without_decision_clear(self) -> None:
        txn_id = "TXN-AF493E2FCD007CAD"
        self.client.get(f"/cases/{txn_id}")
        resp = self.client.post("/decisions", json={
            "txn_id": txn_id, "decision": "block", "is_false_positive": True,
        })
        self.assertEqual(resp.status_code, 400)

    def test_decision_rejects_false_positive_on_a_never_flagged_case(self) -> None:
        txn_id = "TXN-E3A14F5D6ED5855D"  # deterministic normal-pattern (clear) transaction
        self.client.get(f"/cases/{txn_id}")
        resp = self.client.post("/decisions", json={
            "txn_id": txn_id, "decision": "clear", "is_false_positive": True,
        })
        self.assertEqual(resp.status_code, 400)

    def test_case_detail_exposes_analyst_decision_and_false_positive_flag(self) -> None:
        txn_id = "TXN-AF493E2FCD007CAD"
        # Before any decision: no analyst decision recorded yet.
        before = self.client.get(f"/cases/{txn_id}").json()
        self.assertIsNone(before["analyst_decision"])
        self.assertFalse(before["is_false_positive"])

        self.client.post("/decisions", json={
            "txn_id": txn_id, "decision": "clear", "analyst": "fp-test-analyst-2",
            "is_false_positive": True,
        })
        after = self.client.get(f"/cases/{txn_id}").json()
        self.assertEqual(after["analyst_decision"], "clear")
        self.assertTrue(after["is_false_positive"])


if __name__ == "__main__":
    unittest.main()
