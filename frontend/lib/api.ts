import type {
  Case,
  CaseGraphResponse,
  CopilotChatRequest,
  CopilotChatResponse,
  DecisionSubmission,
  HealthResponse,
  PerformanceStats,
  RecentTransaction,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return res.json();
}

export function getRecentTransactions(limit = 25) {
  return apiFetch<{ transactions: RecentTransaction[] }>(
    `/transactions/recent?limit=${limit}`
  );
}

export function getCase(txnId: string) {
  return apiFetch<Case>(`/cases/${txnId}`);
}

export function submitDecision(payload: DecisionSubmission) {
  return apiFetch<{ status?: string }>(`/decisions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Every case the engine has computed this session (unbounded) — unlike
 * getRecentTransactions(), each entry carries full real agent_scores, so
 * the investigation feed's per-signal bars can use it instead of
 * inventing severity data that isn't in the lighter /transactions/recent
 * response. */
export function getCases() {
  return apiFetch<{ cases: Case[] }>(`/cases`);
}

/** The real, masked fraud-ring node/edge graph for a case, or
 * { graph: null } when the transaction has no detected ring. */
export function getCaseGraph(txnId: string) {
  return apiFetch<CaseGraphResponse>(`/cases/${encodeURIComponent(txnId)}/graph`);
}

/** A real liveness check against the backend — never a hardcoded status. */
export function getHealth() {
  return apiFetch<HealthResponse>(`/health`);
}

export function getPerformanceStats() {
  return apiFetch<PerformanceStats>(`/stats/performance`);
}

/** Carries the real HTTP status and the backend's own `detail` message —
 * /copilot/chat returns a clean 503 (key not configured) or 502 (live LLM
 * call failed) with a real explanation in both cases, and the chat panel
 * needs to show that real message rather than a generic failure string. */
export class CopilotApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "CopilotApiError";
    this.status = status;
  }
}

export async function sendCopilotMessage(payload: CopilotChatRequest): Promise<CopilotChatResponse> {
  const res = await fetch(`${API_BASE}/copilot/chat`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data && typeof data.detail === "string"
        ? data.detail
        : `Copilot request failed (${res.status}).`;
    throw new CopilotApiError(res.status, detail);
  }
  return data as CopilotChatResponse;
}
