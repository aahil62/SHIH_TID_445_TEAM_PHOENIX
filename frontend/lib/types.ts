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
