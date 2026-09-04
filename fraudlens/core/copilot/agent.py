"""Copilot investigation assistant.

Hard rule (team design principle): Copilot must never invent a fraud
decision or a fact on its own. Every answer traces back to a real backend
call — the LLM's only two jobs are (1) picking which CaseEngine-backed
tool answers the question, and (2) phrasing that tool's JSON output in
plain language. The constrained-answer principle is structural, not just
a prompt instruction:

  - Stage 1 (`choose_tool`) only ever decides WHICH real tool to call.
  - The tool itself is the only source of facts — it reads straight from
    the same CaseEngine/ReportGenerator the rest of the app uses.
  - Stage 2 (`summarize`) is shown ONLY that tool's JSON output as
    context, so it has nothing else to draw a fact from.
  - When a tool finds nothing (unknown transaction), the agent returns a
    fixed message and never calls the LLM at all — that path can't
    fabricate anything, by construction, not by prompting.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from fraudlens.core.privacy import mask_identifier, mask_ip
from fraudlens.models.schemas import CopilotRequest, CopilotResponse, CopilotToolCall
from fraudlens.runtime import FraudLensRuntime


class CopilotError(Exception):
    """Configuration or backend error — the API layer surfaces this as a 5xx."""


# ── Tools — thin, privacy-aware wrappers over CaseEngine's real state ──────

class CopilotTools:
    """Every method is a real backend call against the same CaseEngine the
    rest of FraudLens uses — never synthesized data. Each returns a JSON-
    serializable dict; `found: False` means there is genuinely nothing on
    record (unknown transaction), which the agent turns into a fixed
    refusal without ever asking the LLM to fill the gap."""

    def __init__(self, runtime: FraudLensRuntime) -> None:
        self._runtime = runtime

    def query_transaction(self, txn_id: str) -> dict[str, Any]:
        case, error = self._get_or_analyze(txn_id)
        if error:
            return error
        txn = case.transaction
        return {
            "found": True,
            "txn_id": case.txn_id,
            "account_id": mask_identifier(txn.account_id),
            "amount": txn.amount,
            "merchant_category": txn.merchant_category,
            "channel": txn.channel,
            "location": txn.location,
            "timestamp": txn.timestamp,
            "decision": case.decision.value,
            "final_score": case.final_score,
            "confidence": case.confidence,
        }

    def explain_decision(self, txn_id: str) -> dict[str, Any]:
        case, error = self._get_or_analyze(txn_id)
        if error:
            return error
        return {
            "found": True,
            "txn_id": case.txn_id,
            "decision": case.decision.value,
            "final_score": case.final_score,
            "confidence": case.confidence,
            "agent_scores": [
                {
                    "agent_name": a.agent_name,
                    "score": a.score,
                    "confidence": a.confidence,
                    "reasons": a.reasons,
                }
                for a in case.agent_scores
            ],
            "explanation_reasons": case.explanation_reasons,
            "recommended_action": case.recommended_action,
        }

    def get_connected_accounts(self, txn_id: str) -> dict[str, Any]:
        case, error = self._get_or_analyze(txn_id)
        if error:
            return error
        ge = case.graph_evidence
        if ge is None:
            return {
                "found": True,
                "has_ring_evidence": False,
                "message": (
                    "No connected accounts or device/IP-sharing evidence was "
                    "detected for this transaction."
                ),
            }
        return {
            "found": True,
            "has_ring_evidence": True,
            "ring_id": ge.ring_id,
            "ring_size": ge.ring_size,
            "connected_accounts": [mask_identifier(a) for a in ge.connected_accounts],
            "shared_devices": [mask_identifier(d) for d in ge.shared_devices],
            "shared_ips": [mask_ip(ip) for ip in ge.shared_ips],
            "suspicious_cluster": ge.suspicious_cluster,
            "graph_density": ge.graph_density,
            "evidence_summary": ge.evidence_summary,
        }

    def find_similar_frauds(self, txn_id: str) -> dict[str, Any]:
        case, error = self._get_or_analyze(txn_id)
        if error:
            return error
        match = case.fraud_dna_match
        if match is None:
            return {
                "found": True,
                "has_match": False,
                "message": "No matching historical fraud pattern was found for this transaction.",
            }
        return {
            "found": True,
            "has_match": True,
            "matched_ring_id": match.matched_ring_id,
            "similarity_score": match.similarity_score,
            "fraud_type": match.fraud_type,
            "modus_operandi": match.modus_operandi,
            "recommendation": match.recommendation,
            "description": match.description,
        }

    def generate_report(self, txn_id: str) -> dict[str, Any]:
        case, error = self._get_or_analyze(txn_id)
        if error:
            return error
        decision = self._runtime.decision_workflow.get_decision(case.case_id)
        report = self._runtime.report_generator.generate(case, analyst_decision=decision)
        return {
            "found": True,
            "report_id": report.report_id,
            "decision": report.decision,
            "engine_recommendation": report.engine_recommendation,
            "risk_score": report.risk_score,
            "confidence": report.confidence,
            "recommended_action": report.recommended_action,
            "report_text": report.report_text,
        }

    def _get_or_analyze(self, txn_id: str) -> tuple[Any, dict[str, Any] | None]:
        if not txn_id:
            return None, {"found": False, "error": "No transaction ID was given."}
        case = self._runtime.engine.get_case_by_txn(txn_id)
        if case is not None:
            return case, None
        try:
            case = self._runtime.analyze(txn_id)
        except ValueError:
            return None, {"found": False, "error": f"No transaction found with ID '{txn_id}'."}
        return case, None


# Name -> description, doubling as the whitelist of tools the LLM may pick.
# Dispatch in CopilotAgent.answer() checks this whitelist BEFORE getattr,
# so a hallucinated tool name can never reach an arbitrary CopilotTools
# method (e.g. the private `_get_or_analyze`).
_TOOL_DESCRIPTIONS: dict[str, str] = {
    "query_transaction": "Look up a transaction's basic details and current fraud decision.",
    "explain_decision": "Explain why a transaction got its fraud decision — per-agent scores and reasons.",
    "get_connected_accounts": "Get graph evidence: accounts, devices, and IPs connected to a transaction's account.",
    "find_similar_frauds": "Find a matching historical fraud ring pattern (Fraud DNA) for a transaction.",
    "generate_report": "Generate the full investigation report for a transaction.",
}


def _tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "txn_id": {
                            "type": "string",
                            "description": "The transaction ID to investigate.",
                        }
                    },
                    "required": ["txn_id"],
                },
            },
        }
        for name, description in _TOOL_DESCRIPTIONS.items()
    ]


# ── LLM abstraction — swappable, and trivially mockable in tests ──────────

@dataclass
class ChosenTool:
    name: str
    arguments: dict[str, Any]


class LLMClient(Protocol):
    def choose_tool(self, question: str, txn_id: str | None) -> ChosenTool | None:
        """Pick which tool answers the question, or None if no tool applies."""
        ...

    def summarize(self, question: str, tool_name: str, tool_result: dict[str, Any]) -> str:
        """Phrase tool_result in plain language. Must add no fact beyond
        what's in tool_result — CopilotAgent never shows this text without
        the tool_result it was generated from alongside it."""
        ...


_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"

_TOOL_ROUTER_SYSTEM_PROMPT = (
    "You are the tool router for FraudLens Copilot, a fraud-investigation "
    "assistant for bank analysts. You never answer fraud questions from your "
    "own knowledge or guess at transaction details. Given an analyst's "
    "question, call exactly one of the available tools to look up real data "
    "about the transaction in question. If the question does not concern a "
    "specific transaction (e.g. a greeting, or something none of the tools "
    "cover), do not call any tool."
)

_SUMMARY_SYSTEM_PROMPT = (
    "You are FraudLens Copilot. You will be given the analyst's question and "
    "a JSON object that is the ONLY source of truth available to you. Answer "
    "the question using ONLY facts present in that JSON — never state a "
    "score, decision, account detail, or piece of evidence that is not "
    "explicitly in the JSON, and never guess at anything the JSON does not "
    "cover. If the JSON says \"found\": false, or says nothing was detected, "
    "say so plainly instead of speculating. Keep the answer to a few "
    "sentences, plain language, no markdown."
)


class GroqLLMClient:
    """Groq's chat-completions API is OpenAI-compatible, so this speaks the
    standard function-calling wire format over plain httpx — no extra SDK
    dependency beyond what the project already has."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL, timeout: float = 20.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def choose_tool(self, question: str, txn_id: str | None) -> ChosenTool | None:
        user_content = question if not txn_id else f"{question}\n\n(Transaction in view: {txn_id})"
        response = self._chat(
            messages=[
                {"role": "system", "content": _TOOL_ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            tools=_tool_specs(),
            tool_choice="auto",
        )
        message = response["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return None

        call = tool_calls[0]
        try:
            arguments = json.loads(call["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            arguments = {}
        if txn_id and not arguments.get("txn_id"):
            arguments["txn_id"] = txn_id
        return ChosenTool(name=call["function"]["name"], arguments=arguments)

    def summarize(self, question: str, tool_name: str, tool_result: dict[str, Any]) -> str:
        response = self._chat(
            messages=[
                {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Analyst's question: {question}\n\n"
                        f"Data from `{tool_name}` (the only source of truth):\n"
                        f"{json.dumps(tool_result, indent=2)}"
                    ),
                },
            ],
        )
        return response["choices"][0]["message"]["content"].strip()

    def _chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self._model, "messages": messages, "temperature": 0.0}
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        try:
            resp = httpx.post(
                _GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise CopilotError(f"Groq API call failed: {exc}") from exc
        return resp.json()


def _default_llm_client() -> LLMClient:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise CopilotError(
            "GROQ_API_KEY is not set. Copilot needs a Groq API key to answer "
            "questions — set the GROQ_API_KEY environment variable (and "
            "optionally GROQ_MODEL) before starting the API."
        )
    model = os.environ.get("GROQ_MODEL", _DEFAULT_MODEL)
    return GroqLLMClient(api_key=api_key, model=model)


# ── Agent ───────────────────────────────────────────────────────────────

class CopilotAgent:
    def __init__(self, runtime: FraudLensRuntime, llm_client: LLMClient | None = None) -> None:
        self._tools = CopilotTools(runtime)
        self._llm = llm_client or _default_llm_client()

    def answer(self, request: CopilotRequest) -> CopilotResponse:
        chosen = self._llm.choose_tool(request.question, request.txn_id)
        if chosen is None:
            return CopilotResponse(
                answer=(
                    "I can only answer questions about a specific transaction using "
                    "FraudLens's own case data — tell me which transaction ID you're "
                    "looking into."
                ),
                tool_calls=[],
            )

        if chosen.name not in _TOOL_DESCRIPTIONS:
            return CopilotResponse(
                answer="I don't have a tool that can answer that.",
                tool_calls=[],
            )

        txn_id = chosen.arguments.get("txn_id") or request.txn_id or ""
        tool_fn = getattr(self._tools, chosen.name)
        result = tool_fn(txn_id)
        call_record = CopilotToolCall(tool=chosen.name, input={"txn_id": txn_id}, output=result)

        if not result.get("found", False):
            # No LLM call on this path — the refusal text comes straight
            # from the tool's own error message, so there's nothing to
            # fabricate even if this branch is reached.
            return CopilotResponse(
                answer=result.get("error", "I couldn't find that information."),
                tool_calls=[call_record],
            )

        answer_text = self._llm.summarize(request.question, chosen.name, result)
        return CopilotResponse(answer=answer_text, tool_calls=[call_record])
