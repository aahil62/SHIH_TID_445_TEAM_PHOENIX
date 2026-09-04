export type Decision = "clear" | "review" | "block" | "block_and_report";

export interface RecentTransaction {
  txn_id: string;
  account_id: string;
  amount: number;
  merchant_category: string;
  timestamp: string;
  final_score: number;
  decision: Decision;
  top_reason: string;
}

export interface Transaction {
  txn_id: string;
  account_id: string;
  amount: number;
  merchant_id: string;
  merchant_category: string;
  device_id: string;
  ip_address: string;
  timestamp: string;
  location: string;
  channel: string;
}

export interface AgentScore {
  agent_name: string;
  score: number;
  confidence: number;
  reasons: string[];
  metadata: Record<string, unknown>;
}

export interface GraphEvidence {
  connected_accounts: string[];
  shared_devices: string[];
  shared_ips: string[];
  shared_merchants: string[];
  ring_size: number;
  ring_id: string | null;
  suspicious_cluster: boolean;
  graph_density: number;
  evidence_summary: string;
}

export interface FraudDnaMatch {
  matched_ring_id: string;
  similarity_score: number;
  fraud_type: string;
  modus_operandi: string;
  recommendation: string;
  matched_profile: Record<string, unknown>;
  description: string;
}

export interface Case {
  case_id: string;
  txn_id: string;
  transaction: Transaction;
  final_score: number;
  decision: Decision;
  confidence: number;
  agent_scores: AgentScore[];
  explanation_reasons: string[];
  graph_evidence: GraphEvidence | null;
  fraud_dna_match: FraudDnaMatch | null;
  recommended_action: string;
  /** "auto_held" when the bounded autonomous-action layer held this case
   * pending review — never a claim that a real transaction was stopped.
   * Cleared the instant an analyst records any decision. */
  system_action: string | null;
  /** True while this transaction's account is under the autonomous
   * velocity restriction that follows an auto-held case — a real,
   * forward-looking consequence, not just a label. Cleared the instant an
   * analyst records a decision on the case that triggered it. */
  account_restricted: boolean;
  created_at: string;
  /** The analyst's own recorded decision, if any — distinct from
   * `decision` above, which is always the engine's own recommendation
   * and never changes once the case is analyzed. Null until an analyst
   * has actually submitted one via POST /decisions. */
  analyst_decision: Decision | null;
  /** True only for a case the engine actually flagged (decision was
   * review/block/block_and_report) that an analyst investigated and
   * confirmed did NOT represent actual fraud — a distinct fact from a
   * transaction that was simply never risky, which also shows
   * decision="clear" but has this False. */
  is_false_positive: boolean;
}

export interface DecisionSubmission {
  txn_id: string;
  decision: Decision;
  notes?: string;
  is_false_positive?: boolean;
}

// ── Fraud-ring graph (GET /cases/{txn_id}/graph) ────────────────────────────
// Node ids/labels are already masked/opaque server-side — see
// fraudlens/core/privacy.py's public_fraud_graph(). Never a raw identifier.

export interface GraphNodePublic {
  id: string;
  node_type: "account" | "device" | "ip" | "merchant";
  label: string;
  is_suspicious: boolean;
}

export interface GraphEdgePublic {
  source: string;
  target: string;
  edge_type: "uses_device" | "uses_ip" | "transacts_with";
  weight: number;
}

export interface CaseGraph {
  nodes: GraphNodePublic[];
  edges: GraphEdgePublic[];
  ring_id: string | null;
  ring_size: number;
  flagged_node_id: string | null;
}

export interface CaseGraphResponse {
  graph: CaseGraph | null;
}

export interface HealthResponse {
  status: string;
}

// ── Model-performance panel (GET /stats/performance) ───────────────────────

export interface AgentPerformance {
  precision: number;
  recall: number;
  f1: number;
  auc_pr: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  n_test: number;
}

export interface PerformanceDataset {
  total: number;
  train: number;
  test: number;
  fraud_ratio_total: number;
  fraud_ratio_test: number;
  pattern_counts: Record<string, number>;
}

export interface ExternalValidation {
  dataset: string;
  total_rows: number;
  train_rows: number;
  test_rows: number;
  fraud_rate: number;
  precision: number;
  recall: number;
  f1: number;
  auc_pr: number;
  fit_seconds: number;
}

export interface PerformanceStats {
  generated_at: string;
  dataset: PerformanceDataset;
  agents: Record<string, AgentPerformance>;
  ensemble: AgentPerformance;
  ml_feature_importances: Record<string, number>;
  external_validation: ExternalValidation | null;
}

// ── Console aggregates (GET /stats/dashboard, /dna/patterns, /audit,
// /reports, /network/summary) ───────────────────────────────────────────

export interface DashboardStats {
  critical_alerts: number;
  pending_reviews: number;
  blocked_transactions: number;
  investigations: number;
  fraud_rings: number;
  transactions_analyzed: number;
  restricted_accounts: number;
  risk_trend: { date: string; avg_score: number; count: number }[];
  agent_averages: { agent_name: string; avg_score: number }[];
}

export interface DnaPattern {
  ring_id: string;
  fraud_type: string;
  name: string;
  description: string;
  matches: number;
  avg_confidence: number | null;
}

export type Tone = "red" | "amber" | "green" | "blue";

export interface AuditLogEvent {
  id: number;
  case_id: string;
  txn_id: string | null;
  event_type: string;
  actor: string;
  occurred_at: string;
  text: string;
  tone: Tone;
}

export interface ReportRow {
  txn_id: string;
  case_id: string;
  risk_pct: number;
  status: string;
  tone: Tone;
  analyst: string;
  created_at: string;
  report_type: string;
}

export interface NetworkRing {
  ring_id: string;
  txn_id: string;
  ring_size: number;
  shared_devices: number;
  shared_ips: number;
  fraud_type: string | null;
  dna_similarity: number | null;
}

export interface NetworkSummary {
  ring_count: number;
  linked_accounts: number;
  shared_devices: number;
  shared_ips: number;
  top_dna_match_pct: number | null;
  rings: NetworkRing[];
}

// ── Auth (POST /auth/login, /auth/signup, GET /auth/me) ─────────────────

export interface AnalystProfile {
  username: string;
  display_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  analyst: AnalystProfile;
}

// ── Copilot (POST /copilot/chat) ────────────────────────────────────────────
// tool_calls is the audit trail proving the answer traces back to a real
// backend call — see fraudlens/core/copilot/agent.py. Always render it.

export interface CopilotToolCall {
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface CopilotChatRequest {
  question: string;
  txn_id?: string;
}

export interface CopilotChatResponse {
  answer: string;
  tool_calls: CopilotToolCall[];
  grounded: boolean;
}
