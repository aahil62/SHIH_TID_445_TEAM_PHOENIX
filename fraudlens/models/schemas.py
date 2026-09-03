"""Shared data contracts for FraudLens.

Every branch builds against these models — they don't change per branch.
Field names and semantics match the team's Level 1 prototype so results
stay comparable across the rebuild.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Enums ─────────────────────────────────────────────────────────────────

class Decision(str, Enum):
    CLEAR = "clear"
    REVIEW = "review"
    BLOCK = "block"
    BLOCK_AND_REPORT = "block_and_report"


# ── Transaction ───────────────────────────────────────────────────────────

class Transaction(BaseModel):
    txn_id: str
    account_id: str
    amount: float
    merchant_id: str
    merchant_category: str
    device_id: str
    ip_address: str
    timestamp: str
    location: str = ""
    channel: str = "online"
    # Ground truth from the synthetic generator — never used by scoring
    # agents at inference time, only for benchmarking and demo labeling.
    is_fraud_demo_label: bool = False
    fraud_pattern_type: str = "normal"


# ── Scoring ───────────────────────────────────────────────────────────────

class AgentScore(BaseModel):
    """Output from a single scoring agent — the contract every agent implements."""
    agent_name: str
    score: float                        # 0.0 - 1.0
    confidence: float = 0.8             # 0.0 - 1.0
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoringResult(BaseModel):
    """Combined output from the ensemble scorer."""
    final_score: float
    decision: Decision
    confidence: float
    agent_scores: list[AgentScore]
    explanation_reasons: list[str]


# ── Graph (populated by feature/graph-behavioral in Stage B) ────────────────

class GraphNode(BaseModel):
    node_id: str
    node_type: str  # account, device, ip, merchant
    label: str
    is_suspicious: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str
    weight: float = 1.0


class FraudGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    ring_id: Optional[str] = None
    ring_size: int = 0


class GraphEvidence(BaseModel):
    connected_accounts: list[str] = Field(default_factory=list)
    shared_devices: list[str] = Field(default_factory=list)
    shared_ips: list[str] = Field(default_factory=list)
    shared_merchants: list[str] = Field(default_factory=list)
    ring_size: int = 0
    ring_id: Optional[str] = None
    suspicious_cluster: bool = False
    graph_density: float = 0.0
    evidence_summary: str = ""


# ── Fraud DNA (populated by feature/graph-behavioral in Stage B) ────────────

class FraudDNAProfile(BaseModel):
    ring_id: str
    ring_size: int
    shared_devices: int
    shared_ips: int
    avg_amount: float
    max_amount: float
    merchant_category_count: int
    velocity_score: float
    graph_density: float
    fraud_type: str
    modus_operandi: str
    first_detected: str
    description: str = ""


class FraudDNAMatch(BaseModel):
    matched_ring_id: str
    similarity_score: float             # 0.0 - 1.0
    fraud_type: str
    modus_operandi: str
    recommendation: str
    matched_profile: FraudDNAProfile
    description: str = ""


# ── Fraud Case — the core output of the engine ──────────────────────────────

class FraudCase(BaseModel):
    case_id: str
    txn_id: str
    transaction: Transaction
    final_score: float
    decision: Decision
    confidence: float
    agent_scores: list[AgentScore]
    explanation_reasons: list[str]
    graph_evidence: Optional[GraphEvidence] = None
    fraud_dna_match: Optional[FraudDNAMatch] = None
    recommended_action: str = ""
    created_at: str = Field(default_factory=_now_iso)


# ── Analyst workflow (populated by feature/graph-behavioral in Stage B) ─────

class AnalystDecision(BaseModel):
    id: int
    case_id: str
    txn_id: str
    decision: str
    analyst: Optional[str] = None
    notes: Optional[str] = None
    decided_at: str
    is_override: bool = False


class AuditEvent(BaseModel):
    id: int
    case_id: str
    txn_id: Optional[str] = None
    event_type: str
    actor: str
    occurred_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Report (populated by main in Stage B) ────────────────────────────────

class FraudReport(BaseModel):
    report_id: str
    case_id: str
    txn_id: str
    account_id: str
    risk_score: float
    decision: str
    engine_recommendation: str
    analyst_decision: Optional[str] = None
    analyst: Optional[str] = None
    analyst_notes: Optional[str] = None
    confidence: float
    agent_scores: list[AgentScore]
    graph_evidence: Optional[GraphEvidence] = None
    fraud_dna_match: Optional[FraudDNAMatch] = None
    recommended_action: str
    report_status: str = "draft"
    generated_at: str = Field(default_factory=_now_iso)
    report_text: str = ""
