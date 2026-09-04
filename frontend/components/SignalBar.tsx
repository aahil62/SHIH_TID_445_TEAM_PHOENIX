import { severityFromScore, SEVERITY_LABEL, SEVERITY_COLOR } from "@/lib/severity";

/** A compact horizontal bar for one real agent's score — the feed's
 * scan-by-color triage affordance and the case screen's risk-signal
 * tree share this. `score`/`label` must come from a real AgentScore;
 * this component only formats and colors them. */
export default function SignalBar({
  label,
  score,
  compact = false,
}: {
  label: string;
  score: number;
  compact?: boolean;
}) {
  const severity = severityFromScore(score);
  const color = SEVERITY_COLOR[severity];
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);

  return (
    <div className="flex items-center gap-2">
      <span
        className={`shrink-0 uppercase tracking-wide ${compact ? "w-28 text-[10px]" : "w-36 text-xs"}`}
        style={{ color: "var(--muted)" }}
      >
        {label}
      </span>
      <span
        className="h-2 flex-1 overflow-hidden rounded-[var(--radius-control)]"
        style={{ backgroundColor: "var(--border)" }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} score`}
      >
        <span
          className="block h-full"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </span>
      <span
        className={`shrink-0 text-right font-semibold ${compact ? "w-14 text-[10px]" : "w-16 text-xs"}`}
        style={{ color }}
      >
        {SEVERITY_LABEL[severity]}
      </span>
    </div>
  );
}
