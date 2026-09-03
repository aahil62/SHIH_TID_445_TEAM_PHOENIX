/** Display labels for real agent_name values returned by the API (never a
 * fabricated agent — this only formats a name that's already present in
 * an AgentScore). Overrides exist only where a generic underscore-split
 * title-case would read poorly (acronyms). */

const AGENT_LABEL_OVERRIDES: Record<string, string> = {
  ml_agent: "ML Agent",
  fraud_dna_agent: "Fraud DNA Agent",
};

export function formatAgentName(agentName: string): string {
  const override = AGENT_LABEL_OVERRIDES[agentName];
  if (override) return override;
  return agentName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
