/** Strips the "[agent_name] " prefix agents attach to reason strings, for plain-language display. */
export function plainReason(reason: string): string {
  return reason.replace(/^\[[a-z_]+\]\s*/i, "");
}
