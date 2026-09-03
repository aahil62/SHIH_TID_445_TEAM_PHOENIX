"""Copilot chat — plain-language investigation Q&A, grounded in real case
data. CopilotAgent is built per-request rather than once at startup so a
missing GROQ_API_KEY only breaks this endpoint, not the whole API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fraudlens.api.state import state
from fraudlens.core.copilot.agent import CopilotAgent, CopilotError
from fraudlens.models.schemas import CopilotRequest

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/chat")
def chat(payload: CopilotRequest) -> dict:
    runtime = state.runtime
    try:
        agent = CopilotAgent(runtime)
    except CopilotError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    response = agent.answer(payload)
    return response.model_dump()
