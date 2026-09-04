import unittest

from fastapi.testclient import TestClient

from fraudlens.api.main import app


class ConsoleApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_dashboard_returns_consistent_aggregate_counts(self) -> None:
        resp = self.client.get("/stats/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for key in (
            "critical_alerts", "pending_reviews", "blocked_transactions",
            "investigations", "fraud_rings", "transactions_analyzed",
        ):
            self.assertIn(key, data)
            self.assertGreaterEqual(data[key], 0)
        # investigations (non-clear) must be at least the blocked count,
        # since blocked is a subset of non-clear decisions.
        self.assertGreaterEqual(data["investigations"], data["blocked_transactions"])
        self.assertGreaterEqual(data["blocked_transactions"], data["critical_alerts"])
        self.assertIsInstance(data["risk_trend"], list)
        self.assertIsInstance(data["agent_averages"], list)
        agent_names = {a["agent_name"] for a in data["agent_averages"]}
        self.assertIn("ml_agent", agent_names)
        self.assertIn("fraud_dna_agent", agent_names)

    def test_dashboard_agent_averages_are_valid_probabilities(self) -> None:
        data = self.client.get("/stats/dashboard").json()
        for a in data["agent_averages"]:
            self.assertGreaterEqual(a["avg_score"], 0.0)
            self.assertLessEqual(a["avg_score"], 1.0)

    def test_dna_patterns_lists_the_seed_library(self) -> None:
        resp = self.client.get("/dna/patterns")
        self.assertEqual(resp.status_code, 200)
        patterns = resp.json()["patterns"]
        self.assertGreaterEqual(len(patterns), 5)  # 5 seed profiles
        ring_ids = {p["ring_id"] for p in patterns}
        self.assertIn("SEED-BUST-OUT", ring_ids)
        for p in patterns:
            self.assertGreaterEqual(p["matches"], 0)
            if p["avg_confidence"] is not None:
                self.assertGreaterEqual(p["avg_confidence"], 0.0)
                self.assertLessEqual(p["avg_confidence"], 1.0)

    def test_dna_patterns_match_counts_reflect_real_analyzed_cases(self) -> None:
        # TXN-AF493E2FCD007CAD is a known deterministic case matching
        # SEED-BUST-OUT at 81% (see test_api.py) — that real match must be
        # reflected in the aggregate count, not a placeholder number.
        self.client.get("/cases/TXN-AF493E2FCD007CAD")
        patterns = self.client.get("/dna/patterns").json()["patterns"]
        bust_out = next(p for p in patterns if p["ring_id"] == "SEED-BUST-OUT")
        self.assertGreaterEqual(bust_out["matches"], 1)

    def test_global_audit_returns_real_events_with_plain_text(self) -> None:
        resp = self.client.get("/audit")
        self.assertEqual(resp.status_code, 200)
        events = resp.json()["events"]
        self.assertGreater(len(events), 0)
        for e in events:
            self.assertIn("text", e)
            self.assertTrue(e["text"])
            self.assertIn(e["tone"], ("red", "amber", "green", "blue"))
            self.assertIn("case_id", e)

    def test_global_audit_respects_limit(self) -> None:
        events = self.client.get("/audit?limit=3").json()["events"]
        self.assertLessEqual(len(events), 3)

    def test_global_audit_reflects_a_real_analyst_decision(self) -> None:
        txn_id = self.client.get("/transactions/recent?limit=1").json()["transactions"][0]["txn_id"]
        self.client.get(f"/cases/{txn_id}")
        self.client.post("/decisions", json={
            "txn_id": txn_id, "decision": "review", "analyst": "console-test-analyst",
        })
        events = self.client.get("/audit?limit=200").json()["events"]
        matching = [e for e in events if e["txn_id"] == txn_id and e["event_type"] == "analyst_decision"]
        self.assertTrue(matching)
        self.assertIn("console-test-analyst", matching[0]["text"])

    def test_reports_list_returns_rows_sorted_highest_risk_first(self) -> None:
        resp = self.client.get("/reports?limit=20")
        self.assertEqual(resp.status_code, 200)
        rows = resp.json()["rows"]
        self.assertEqual(len(rows), 20)
        risk = [r["risk_pct"] for r in rows]
        self.assertEqual(risk, sorted(risk, reverse=True))
        for r in rows:
            self.assertIn("txn_id", r)
            self.assertIn("status", r)
            self.assertIn("report_type", r)

    def test_reports_list_shows_real_decision_status_when_recorded(self) -> None:
        txn_id = self.client.get("/transactions/recent?limit=1").json()["transactions"][0]["txn_id"]
        self.client.get(f"/cases/{txn_id}")
        self.client.post("/decisions", json={
            "txn_id": txn_id, "decision": "block", "analyst": "reports-test-analyst",
        })
        # limit comfortably above the full synthetic dataset size (1,037)
        # so the queried txn is guaranteed to appear regardless of rank.
        rows = self.client.get("/reports?limit=2000").json()["rows"]
        row = next(r for r in rows if r["txn_id"] == txn_id)
        self.assertEqual(row["status"], "BLOCK")
        self.assertEqual(row["analyst"], "reports-test-analyst")

    def test_network_summary_finds_a_known_ring(self) -> None:
        resp = self.client.get("/network/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["ring_count"], 0)
        self.assertGreater(data["linked_accounts"], 0)
        ring_ids = {r["ring_id"] for r in data["rings"]}
        # deterministic ring from TXN-AF493E2FCD007CAD (see test_api.py)
        self.assertTrue(any(r["ring_size"] >= 2 for r in data["rings"]))
        self.assertGreater(len(ring_ids), 0)

    def test_network_summary_ring_txn_ids_are_real_and_fetchable(self) -> None:
        data = self.client.get("/network/summary").json()
        self.assertGreater(len(data["rings"]), 0)
        sample_txn = data["rings"][0]["txn_id"]
        case_resp = self.client.get(f"/cases/{sample_txn}")
        self.assertEqual(case_resp.status_code, 200)
        self.assertIsNotNone(case_resp.json()["graph_evidence"])


if __name__ == "__main__":
    unittest.main()
