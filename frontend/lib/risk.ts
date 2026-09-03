import type { Decision } from "./types";

export const DECISION_LABEL: Record<Decision, string> = {
  clear: "Clear",
  review: "Review",
  block: "Block",
  block_and_report: "Block & Report",
};

export const DECISION_TONE: Record<
  Decision,
  { fg: string; bg: string }
> = {
  clear: { fg: "var(--risk-low)", bg: "var(--risk-low-bg)" },
  review: { fg: "var(--risk-medium)", bg: "var(--risk-medium-bg)" },
  block: { fg: "var(--risk-high)", bg: "var(--risk-high-bg)" },
  block_and_report: { fg: "var(--risk-critical)", bg: "var(--risk-critical-bg)" },
};

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function formatAmount(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
