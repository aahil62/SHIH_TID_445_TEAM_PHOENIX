"""FraudLens — FastAPI application.

Run with: uvicorn fraudlens.api.main:app --reload --port 8001
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fraudlens.api.routes.cases import router as cases_router
from fraudlens.api.routes.decisions import router as decisions_router
from fraudlens.api.routes.health import router as health_router
from fraudlens.api.routes.reports import router as reports_router
from fraudlens.api.routes.transactions import router as transactions_router
from fraudlens.api.state import state
from fraudlens.runtime import build_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.runtime = build_runtime()
    yield


app = FastAPI(
    title="FraudLens API",
    description="AI Fraud Intelligence & Regulatory CaseOps Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Wildcard origin + credentials is an invalid combination — pin to the
# local frontend dev origin, override via FRAUDLENS_CORS_ORIGINS (comma
# separated) once feature/frontend has a deployed URL.
_cors_origins = os.environ.get(
    "FRAUDLENS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(transactions_router)
app.include_router(cases_router)
app.include_router(reports_router)
app.include_router(decisions_router)
