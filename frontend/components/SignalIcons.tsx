import type { AgentScore } from "@/lib/types";
import { severityFromScore, SEVERITY_LABEL, SEVERITY_COLOR } from "@/lib/severity";
import { formatAgentName } from "@/lib/agents";
import { AgentIcon } from "@/lib/agentIcons";

/** Compact glanceable row for list contexts — every real agent_scores
 * entry as a small colored icon (severity-colored, real agent identity),
 * instead of full labeled bars. Full detail (score, reasons) stays on
 * the case page; this just shows, at a glance, which real signals exist
 * and roughly how severe each is — hover/focus reveals the exact
 * numbers via the native title tooltip, nothing hidden, just compacted. */
export default function SignalIcons({ scores }: { scores: AgentScore[] }) {
  if (scores.length === 0) return null;
  const sorted = [...scores].sort((a, b) => b.score - a.score);

  return (
    <div className="flex flex-wrap items-center gap-1.5" role="list" aria-label="Risk signals">
      {sorted.map((s) => {
        const severity = severityFromScore(s.score);
        const color = SEVERITY_COLOR[severity];
        const label = formatAgentName(s.agent_name);
        return (
          <span
            key={s.agent_name}
            role="listitem"
            title={`${label}: ${SEVERITY_LABEL[severity]} (${Math.round(s.score * 100)}%)`}
            className="flex h-6 w-6 items-center justify-center rounded-[var(--radius-control)] border"
            style={{ borderColor: color, color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}
          >
            <AgentIcon agentName={s.agent_name} className="h-3.5 w-3.5" />
          </span>
        );
      })}
    </div>
  );
}
