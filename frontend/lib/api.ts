import type { Case, DecisionSubmission, RecentTransaction } from "./types";

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
