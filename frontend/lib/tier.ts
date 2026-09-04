/** Terminal-style risk-tier labels for the investigation console — a
 * relabeling of the real Decision axis (see lib/risk.ts's DECISION_TONE,
 * which this reuses unmodified for color), not a new data source. Kept as
 * 4 real tiers rather than collapsing block/block_and_report into one
 * "HIGH" label, since block_and_report is a real, more-severe state the
 * backend already distinguishes. */
import type { Decision } from "./types";

export const RISK_TIER_LABEL: Record<Decision, string> = {
  clear: "LOW RISK",
  review: "MEDIUM RISK",
  block: "HIGH RISK",
  block_and_report: "CRITICAL",
};
