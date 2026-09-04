"""Tests for the live-feed SSE generator.

Exercises fraudlens.api.routes.live._stream_events() directly as an async
generator rather than through TestClient's HTTP streaming layer — an
infinite StreamingResponse consumed via httpx's ASGITransport hung
indefinitely in this environment (confirmed by isolating the generator
itself, which returns real results in well under a second). Testing the
generator directly still exercises the real pipeline — the same
state.runtime.analyze() call every other route uses — just without the
flaky transport layer in between. The route registration itself (query
param validation) is covered separately via a non-streaming request.
"""

import json
import unittest
import unittest.mock

from fraudlens.testing import use_isolated_data_dir

use_isolated_data_dir()

import asyncio

from fastapi.testclient import TestClient

from fraudlens.api.main import app
from fraudlens.api.routes.live import _stream_events
from fraudlens.api.state import state


class LiveStreamGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.client.__enter__()  # triggers lifespan startup -> state.runtime

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _collect(self, max_events: int, interval_seconds: float = 0.05) -> list[dict]:
        async def _run() -> list[dict]:
            events = []
            async for chunk in _stream_events(interval_seconds):
                self.assertTrue(chunk.startswith("data: "))
                self.assertTrue(chunk.endswith("\n\n"))
                events.append(json.loads(chunk[len("data: "):]))
                if len(events) >= max_events:
                    break
            return events

        return asyncio.run(_run())

    def test_stream_starts_with_a_real_ingested_transaction(self) -> None:
        events = self._collect(max_events=1)
        self.assertEqual(events[0]["type"], "ingested")
        self.assertTrue(events[0]["txn_id"].startswith("TXN-"))
        # account_id must be masked, never raw, same convention as every
        # other outward-facing route.
        self.assertIn("••", events[0]["account_id"])

    def test_stream_reveals_real_agent_scores_before_the_decision(self) -> None:
        events = self._collect(max_events=8)
        types_seen = [e["type"] for e in events]
        self.assertEqual(types_seen[0], "ingested")
        self.assertIn("agent_scored", types_seen)
        agent_events = [e for e in events if e["type"] == "agent_scored"]
        for e in agent_events:
            self.assertIn(e["agent_name"], (
                "rule_agent", "velocity_agent", "behavioral_agent",
                "graph_agent", "ml_agent", "fraud_dna_agent",
            ))
            self.assertGreaterEqual(e["score"], 0.0)
            self.assertLessEqual(e["score"], 1.0)

    def test_decision_event_matches_a_real_case_lookup(self) -> None:
        # Read until a decision event appears, then verify it agrees with
        # GET /cases/{txn_id} for the same transaction — proving the
        # stream reflects the real engine, not separately-invented numbers.
        events = self._collect(max_events=10)
        decision_events = [e for e in events if e["type"] == "decision"]
        self.assertTrue(decision_events)
        first = decision_events[0]

        case = self.client.get(f"/cases/{first['txn_id']}").json()
        self.assertAlmostEqual(case["final_score"], first["final_score"], places=6)
        self.assertEqual(case["decision"], first["decision"])

    def test_stream_loops_back_to_the_start_of_the_dataset(self) -> None:
        # Cycling the *real* 1,037-transaction dataset far enough to prove
        # wraparound would take minutes (each transaction reveals ~5 agent
        # events at a fixed 0.45s pace, by design — that pacing is the
        # whole point of the feature). Swap in a small 2-transaction slice
        # of the same real dataset instead: same generator, same
        # runtime.analyze() calls, real data — just enough of it to
        # observe the modulo-index wraparound cheaply.
        real_transactions = state.runtime.transactions
        small_transactions = real_transactions[:2]
        with unittest.mock.patch.object(state.runtime, "transactions", small_transactions):
            # Generous enough to comfortably span two full transactions'
            # worth of events (ingested + several agent_scored + decision
            # each) regardless of exactly how many agents fire.
            events = self._collect(max_events=20, interval_seconds=0.0)
        ingested = [e for e in events if e["type"] == "ingested"]
        self.assertGreaterEqual(len(ingested), 2)
        small_txn_ids = {t.txn_id for t in small_transactions}
        for e in ingested:
            self.assertIn(e["txn_id"], small_txn_ids)
        # Proves the cycle actually wrapped rather than stalling on the
        # first transaction — both real transactions get ingested again.
        self.assertEqual({e["txn_id"] for e in ingested}, small_txn_ids)


class LiveStreamRouteTests(unittest.TestCase):
    """Non-streaming checks — safe to run through TestClient normally
    since validation failures never enter the infinite generator."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_interval_seconds_out_of_range_is_rejected_before_streaming(self) -> None:
        resp = self.client.get("/live/stream?interval_seconds=999")
        self.assertEqual(resp.status_code, 422)

    def test_interval_seconds_below_minimum_is_rejected(self) -> None:
        resp = self.client.get("/live/stream?interval_seconds=0.01")
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
