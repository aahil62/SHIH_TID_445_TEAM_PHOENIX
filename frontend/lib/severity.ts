/** Per-signal severity, derived from a real AgentScore.score (0-1) — used
 * for the feed's signal bars and the case screen's risk-signal tree.
 * Reuses the existing risk-color tokens (globals.css) rather than
 * inventing a second color language; thresholds are a display-only
 * bucketing of a real number, never a fabricated value. */

export type Severity = "high" | "medium" | "low";

export function severityFromScore(score: number): Severity {
  if (score >= 0.7) return "high";
  if (score >= 0.4) return "medium";
  return "low";
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  high: "HIGH",
  medium: "MEDIUM",
  low: "LOW",
};

export const SEVERITY_COLOR: Record<Severity, string> = {
  high: "var(--risk-high)",
  medium: "var(--risk-medium)",
  low: "var(--risk-low)",
};
