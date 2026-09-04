"""Live transaction feed — the real ingest -> validate -> decide pipeline,
observable as it happens, instead of the whole dataset being silently
pre-computed at startup.

Nothing here is faked or pre-recorded: each transaction is analyzed by
calling the real runtime.analyze() at stream time, agent by agent, in the
same order and with the same weights as every other route in this API.
The only presentation choice is *pacing* — a small delay between each
agent's reveal and between transactions, so a human watching can actually
see six independent signals contribute to one decision, rather than a
sub-100ms computation flashing past unreadably. The analysis itself is
not slowed down or altered; the delay is purely in how quickly each
already-computed result is revealed to the stream.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from fraudlens.api.state import state
from fraudlens.core.privacy import mask_identifier

router = APIRouter(prefix="/live", tags=["live"])

_AGENT_REVEAL_DELAY_SECONDS = 0.45
_DEFAULT_TRANSACTION_INTERVAL_SECONDS = 2.5


def _sse(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


async def _stream_events(interval_seconds: float) -> AsyncIterator[str]:
    runtime = state.runtime
    transactions = runtime.transactions

    index = 0
    while True:
        txn = transactions[index % len(transactions)]
        index += 1

        yield _sse(
            "ingested",
            {
                "txn_id": txn.txn_id,
                "account_id": mask_identifier(txn.account_id),
                "amount": txn.amount,
                "merchant_category": txn.merchant_category,
                "channel": txn.channel,
                "timestamp": txn.timestamp,
            },
        )
        await asyncio.sleep(0.3)

        # The real pipeline, computed now — not looked up from a cache
        # built at server startup.
        case = runtime.analyze(txn.txn_id)

        for agent_score in case.agent_scores:
            if agent_score.confidence <= 0.0:
                continue  # abstained (e.g. fraud_dna_agent with no ring) — nothing to reveal
            yield _sse(
                "agent_scored",
                {
                    "txn_id": txn.txn_id,
                    "agent_name": agent_score.agent_name,
                    "score": agent_score.score,
                    "confidence": agent_score.confidence,
                    "reason": agent_score.reasons[0] if agent_score.reasons else "",
                },
            )
            await asyncio.sleep(_AGENT_REVEAL_DELAY_SECONDS)

        yield _sse(
            "decision",
            {
                "txn_id": txn.txn_id,
                "final_score": case.final_score,
                "confidence": case.confidence,
                "decision": case.decision.value,
            },
        )

        if case.system_action == "auto_held":
            await asyncio.sleep(0.3)
            yield _sse(
                "autonomous_action",
                {
                    "txn_id": txn.txn_id,
                    "system_action": case.system_action,
                    "account_id": mask_identifier(txn.account_id),
                },
            )

        await asyncio.sleep(max(0.0, interval_seconds))


@router.get("/stream")
async def stream_live_feed(
    interval_seconds: float = Query(_DEFAULT_TRANSACTION_INTERVAL_SECONDS, ge=0.5, le=15.0),
) -> StreamingResponse:
    return StreamingResponse(
        _stream_events(interval_seconds),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx-style proxy buffering, if any sits in front
        },
    )
