import type { Decision } from "@/lib/types";
import { DECISION_LABEL, DECISION_TONE } from "@/lib/risk";

export default function DecisionBadge({ decision }: { decision: Decision }) {
  const tone = DECISION_TONE[decision];
  return (
    <span
      className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium"
      style={{ color: tone.fg, backgroundColor: tone.bg }}
    >
      {DECISION_LABEL[decision]}
    </span>
  );
}
