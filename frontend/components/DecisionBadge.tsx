import type { Decision } from "@/lib/types";
import { DECISION_LABEL, DECISION_TONE } from "@/lib/risk";

export default function DecisionBadge({ decision }: { decision: Decision }) {
  const tone = DECISION_TONE[decision];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-[var(--radius-control)] px-2.5 py-1 text-xs font-semibold"
      style={{ color: tone.fg, backgroundColor: tone.bg }}
    >
      <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-current" aria-hidden="true" />
      {DECISION_LABEL[decision]}
    </span>
  );
}
