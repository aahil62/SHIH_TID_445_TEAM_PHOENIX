"""Copilot tests.

No real LLM calls anywhere here — that would cost API credits and make
CI flaky. Instead:
  - CopilotTools is tested directly against a real CaseEngine (same
    fixture shape as test_case_engine_fraud_dna.py), so "correct
    structured data against real CaseEngine state" is checked by
    comparing tool output to the engine's own case objects.
  - CopilotAgent is tested with a fake LLMClient, to prove the
    constrained-answer principle structurally: the tool's real output is
    exactly what gets shown to the (fake) summarizer, an unknown
    transaction never reaches the LLM at all, and a hallucinated/private
    tool name is refused rather than dispatched.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from fraudlens.core.cases.case_engine import CaseEngine
from fraudlens.core.cases.decision_workflow import DecisionWorkflow
from fraudlens.core.copilot.agent import ChosenTool, CopilotAgent, CopilotError, CopilotTools
from fraudlens.core.dna.store import FraudDNAStore
from fraudlens.core.reports.generator import ReportGenerator
from fraudlens.core.scoring.graph_agent import GraphAgent
from fraudlens.models.schemas import CopilotRequest, Transaction
from fraudlens.runtime import FraudLensRuntime


def _txn(txn_id, account_id, device_id, ip_address, amount, minute, merchant_id="M_CT") -> Transaction:
    return Transaction(
        txn_id=txn_id,
        account_id=account_id,
        amount=amount,
        merchant_id=merchant_id,
        merchant_category="digital_goods",
        device_id=device_id,
        ip_address=ip_address,
        timestamp=f"2026-09-01T10:{minute:02d}:00+00:00",
    )


def _card_testing_ring_txns() -> list[Transaction]:
    """Same fixture shape as test_case_engine_fraud_dna.py: 3 accounts on
    one shared device/IP, tiny amounts, tight window — matches the seeded
    card-testing Fraud DNA pattern."""
    txns = []
    amounts = [2.0, 3.5, 5.0, 6.5, 8.0, 9.0]
    accounts = ["RING-A1", "RING-A2", "RING-A3"]
    for i, (minute, account_id) in enumerate(zip(range(6), accounts * 2)):
        txns.append(_txn(f"R{i}", account_id, "D_CT", "IP_CT", amounts[i % len(amounts)], minute))
    return txns


def _normal_txn() -> Transaction:
    return Transaction(
        txn_id="N1",
        account_id="NORMAL-A1",
        amount=42.0,
        merchant_id="M_NORMAL",
        merchant_category="groceries",
        device_id="D_NORMAL",
        ip_address="9.9.9.9",
        timestamp="2026-09-01T12:00:00+00:00",
    )


class _FakeLLMClient:
    """Records every summarize() call so tests can assert exactly what
    context the (fake) LLM was given — the concrete, automatable check for
    "the reply only ever contains facts from a tool result"."""

    def __init__(self, chosen: ChosenTool | None) -> None:
        self._chosen = chosen
        self.summarize_calls: list[tuple[str, str, dict]] = []
        self.summary_text = "FAKE SUMMARY"

    def choose_tool(self, question: str, txn_id):
        return self._chosen

    def summarize(self, question: str, tool_name: str, tool_result: dict) -> str:
        self.summarize_calls.append((question, tool_name, tool_result))
        return self.summary_text


class _CopilotFixture(unittest.TestCase):
    """Shared real-engine setup for both the tool tests and the agent tests."""

    def setUp(self) -> None:
        self._cases_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._cases_tmp.close()
        self._dna_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._dna_tmp.close()
        os.remove(self._dna_tmp.name)  # let FraudDNAStore auto-seed it
        self._decisions_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._decisions_tmp.close()
        self._audit_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._audit_tmp.close()
        for path in (self._cases_tmp.name, self._dna_tmp.name, self._decisions_tmp.name, self._audit_tmp.name):
            self.addCleanup(lambda p=path: os.path.exists(p) and os.remove(p))

        self.ring_txns = _card_testing_ring_txns()
        self.normal_txn = _normal_txn()
        transactions = self.ring_txns + [self.normal_txn]

        graph_agent = GraphAgent()
        graph_agent.build_index(transactions)
        self.engine = CaseEngine(
            transactions,
            agents=[graph_agent],
            cases_path=self._cases_tmp.name,
            dna_store=FraudDNAStore(path=self._dna_tmp.name),
        )
        self.runtime = FraudLensRuntime(
            engine=self.engine,
            decision_workflow=DecisionWorkflow(
                decisions_path=self._decisions_tmp.name, audit_path=self._audit_tmp.name,
            ),
            report_generator=ReportGenerator(),
            transactions=transactions,
            dna_store=FraudDNAStore(path=self._dna_tmp.name),
        )
        self.tools = CopilotTools(self.runtime)


class CopilotToolsTests(_CopilotFixture):
    def test_query_transaction_matches_engine_state(self) -> None:
        txn_id = self.ring_txns[0].txn_id
        case = self.engine.get_case_by_txn(txn_id) or self.engine.analyze(txn_id)

        result = self.tools.query_transaction(txn_id)

        self.assertTrue(result["found"])
        self.assertEqual(result["txn_id"], case.txn_id)
        self.assertEqual(result["decision"], case.decision.value)
        self.assertEqual(result["final_score"], case.final_score)
        self.assertEqual(result["confidence"], case.confidence)
        self.assertEqual(result["amount"], case.transaction.amount)
        # Raw account id must never leak out of a Copilot tool.
        self.assertNotEqual(result["account_id"], case.transaction.account_id)

    def test_query_transaction_scores_if_not_yet_analyzed(self) -> None:
        txn_id = self.normal_txn.txn_id
        self.assertIsNone(self.engine.get_case_by_txn(txn_id))

        result = self.tools.query_transaction(txn_id)

        self.assertTrue(result["found"])
        self.assertIsNotNone(self.engine.get_case_by_txn(txn_id))

    def test_query_transaction_unknown_id(self) -> None:
        result = self.tools.query_transaction("TXN-DOES-NOT-EXIST")
        self.assertFalse(result["found"])
        self.assertIn("TXN-DOES-NOT-EXIST", result["error"])

    def test_query_transaction_empty_id(self) -> None:
        result = self.tools.query_transaction("")
        self.assertFalse(result["found"])

    def test_explain_decision_matches_case_agent_scores(self) -> None:
        txn_id = self.ring_txns[0].txn_id
        case = self.engine.analyze(txn_id)

        result = self.tools.explain_decision(txn_id)

        self.assertTrue(result["found"])
        self.assertEqual(len(result["agent_scores"]), len(case.agent_scores))
        for expected, actual in zip(case.agent_scores, result["agent_scores"]):
            self.assertEqual(actual["agent_name"], expected.agent_name)
            self.assertEqual(actual["score"], expected.score)
            self.assertEqual(actual["reasons"], expected.reasons)
        self.assertEqual(result["explanation_reasons"], case.explanation_reasons)
        self.assertEqual(result["recommended_action"], case.recommended_action)

    def test_get_connected_accounts_for_ring_transaction(self) -> None:
        txn_id = self.ring_txns[0].txn_id
        case = self.engine.analyze(txn_id)
        self.assertIsNotNone(case.graph_evidence)  # sanity: fixture actually forms a ring

        result = self.tools.get_connected_accounts(txn_id)

        self.assertTrue(result["found"])
        self.assertTrue(result["has_ring_evidence"])
        self.assertEqual(result["ring_size"], case.graph_evidence.ring_size)
        self.assertEqual(len(result["shared_devices"]), len(case.graph_evidence.shared_devices))
        # Masked, not raw.
        for device in result["shared_devices"]:
            self.assertNotIn("D_CT", device)

    def test_get_connected_accounts_for_normal_transaction(self) -> None:
        result = self.tools.get_connected_accounts(self.normal_txn.txn_id)
        self.assertTrue(result["found"])
        self.assertFalse(result["has_ring_evidence"])
        self.assertIn("message", result)

    def test_find_similar_frauds_matches_seeded_pattern(self) -> None:
        txn_id = self.ring_txns[0].txn_id
        case = self.engine.analyze(txn_id)
        self.assertIsNotNone(case.fraud_dna_match)  # sanity

        result = self.tools.find_similar_frauds(txn_id)

        self.assertTrue(result["found"])
        self.assertTrue(result["has_match"])
        self.assertEqual(result["matched_ring_id"], case.fraud_dna_match.matched_ring_id)
        self.assertEqual(result["similarity_score"], case.fraud_dna_match.similarity_score)

    def test_find_similar_frauds_no_match_for_normal_transaction(self) -> None:
        result = self.tools.find_similar_frauds(self.normal_txn.txn_id)
        self.assertTrue(result["found"])
        self.assertFalse(result["has_match"])

    def test_generate_report_contains_real_case_data(self) -> None:
        txn_id = self.ring_txns[0].txn_id
        case = self.engine.analyze(txn_id)

        result = self.tools.generate_report(txn_id)

        self.assertTrue(result["found"])
        self.assertEqual(result["decision"], case.decision.value)
        self.assertIn("Investigation Report", result["report_text"])

    def test_generate_report_unknown_id(self) -> None:
        result = self.tools.generate_report("TXN-DOES-NOT-EXIST")
        self.assertFalse(result["found"])


class CopilotAgentGroundingTests(_CopilotFixture):
    """The constrained-answer principle, verified structurally rather than
    by trusting an LLM's honesty."""

    def test_summarizer_receives_exactly_the_tool_output(self) -> None:
        txn_id = self.ring_txns[0].txn_id
        expected = self.tools.explain_decision(txn_id)  # ground truth, computed directly

        llm = _FakeLLMClient(chosen=ChosenTool(name="explain_decision", arguments={"txn_id": txn_id}))
        agent = CopilotAgent(self.runtime, llm_client=llm)

        response = agent.answer(CopilotRequest(question="why was this flagged?", txn_id=txn_id))

        self.assertEqual(len(llm.summarize_calls), 1)
        _, tool_name, tool_result = llm.summarize_calls[0]
        self.assertEqual(tool_name, "explain_decision")
        self.assertEqual(tool_result, expected)
        self.assertEqual(response.answer, llm.summary_text)
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].output, expected)
        self.assertTrue(response.grounded)

    def test_unknown_transaction_never_reaches_the_llm_summarizer(self) -> None:
        llm = _FakeLLMClient(
            chosen=ChosenTool(name="query_transaction", arguments={"txn_id": "TXN-GHOST"})
        )
        agent = CopilotAgent(self.runtime, llm_client=llm)

        response = agent.answer(CopilotRequest(question="what happened with TXN-GHOST?"))

        self.assertEqual(llm.summarize_calls, [])  # never asked to narrate a guess
        self.assertIn("TXN-GHOST", response.answer)
        self.assertEqual(len(response.tool_calls), 1)
        self.assertFalse(response.tool_calls[0].output["found"])

    def test_no_relevant_tool_gives_fixed_clarifying_answer(self) -> None:
        llm = _FakeLLMClient(chosen=None)
        agent = CopilotAgent(self.runtime, llm_client=llm)

        response = agent.answer(CopilotRequest(question="hello there"))

        self.assertEqual(llm.summarize_calls, [])
        self.assertEqual(response.tool_calls, [])
        self.assertIn("transaction", response.answer.lower())

    def test_hallucinated_tool_name_is_refused_not_dispatched(self) -> None:
        txn_id = self.ring_txns[0].txn_id
        # A malicious/confused model naming a private method — must not
        # reach CopilotTools._get_or_analyze via getattr.
        llm = _FakeLLMClient(chosen=ChosenTool(name="_get_or_analyze", arguments={"txn_id": txn_id}))
        agent = CopilotAgent(self.runtime, llm_client=llm)

        response = agent.answer(CopilotRequest(question="anything", txn_id=txn_id))

        self.assertEqual(llm.summarize_calls, [])
        self.assertEqual(response.tool_calls, [])
        self.assertIn("don't have a tool", response.answer)

    def test_unrelated_nonexistent_tool_name_is_refused(self) -> None:
        llm = _FakeLLMClient(chosen=ChosenTool(name="delete_all_cases", arguments={}))
        agent = CopilotAgent(self.runtime, llm_client=llm)

        response = agent.answer(CopilotRequest(question="anything"))

        self.assertEqual(llm.summarize_calls, [])
        self.assertEqual(response.tool_calls, [])

    def test_request_txn_id_used_when_llm_omits_argument(self) -> None:
        txn_id = self.normal_txn.txn_id
        llm = _FakeLLMClient(chosen=ChosenTool(name="query_transaction", arguments={}))
        agent = CopilotAgent(self.runtime, llm_client=llm)

        response = agent.answer(CopilotRequest(question="tell me about this one", txn_id=txn_id))

        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].input["txn_id"], txn_id)
        self.assertTrue(response.tool_calls[0].output["found"])


class CopilotConfigTests(_CopilotFixture):
    def test_missing_api_key_raises_copilot_error_not_a_silent_fallback(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GROQ_API_KEY", None)
            with self.assertRaises(CopilotError):
                CopilotAgent(self.runtime)


if __name__ == "__main__":
    unittest.main()
