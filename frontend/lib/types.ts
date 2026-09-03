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
  created_at: string;
}

export interface DecisionSubmission {
  txn_id: string;
  decision: Decision;
  analyst?: string;
  notes?: string;
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
