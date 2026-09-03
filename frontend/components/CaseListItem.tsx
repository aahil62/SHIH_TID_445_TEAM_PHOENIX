import Link from "next/link";
import type { Case } from "@/lib/types";
import { formatAmount, formatTimestamp, DECISION_TONE } from "@/lib/risk";
import { RISK_TIER_LABEL } from "@/lib/tier";
import { formatAgentName } from "@/lib/agents";
import MaskedId from "./MaskedId";
import SignalBar from "./SignalBar";

/** One card in the investigation feed / case list — real tier, amount,
 * masked account, and a per-signal bar for every real agent_scores entry
 * on this case (no fixed/fabricated signal set; whatever the case
 * actually has). */
export default function CaseListItem({ item }: { item: Case }) {
  const tone = DECISION_TONE[item.decision];
  const signals = [...item.agent_scores].sort((a, b) => b.score - a.score);

  return (
    <Link
      href={`/case?txn_id=${encodeURIComponent(item.txn_id)}`}
      className="block rounded-[var(--radius-panel)] border px-4 py-3 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--panel)",
        borderLeft: `3px solid ${tone.fg}`,
        boxShadow: "var(--shadow-panel)",
      }}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold tracking-wide" style={{ color: tone.fg }}>
            {RISK_TIER_LABEL[item.decision]}
          </span>
          <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
            {item.txn_id}
          </span>
        </div>
        <span className="text-[11px]" style={{ color: "var(--muted)" }}>
          {formatTimestamp(item.transaction.timestamp)}
        </span>
      </div>

      <div className="mt-1.5 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
        <span className="font-mono font-semibold">{formatAmount(item.transaction.amount)}</span>
        <span style={{ color: "var(--muted)" }}>
          Account <MaskedId value={item.transaction.account_id} />
        </span>
        <span className="text-xs capitalize" style={{ color: "var(--muted)" }}>
          {item.transaction.merchant_category.replace(/_/g, " ")}
        </span>
      </div>

      {signals.length > 0 ? (
        <div className="mt-3 flex flex-col gap-1.5 border-t pt-3" style={{ borderColor: "var(--border)" }}>
          {signals.map((s) => (
            <SignalBar key={s.agent_name} label={formatAgentName(s.agent_name)} score={s.score} compact />
          ))}
        </div>
      ) : (
        <p className="mt-3 border-t pt-3 text-[11px]" style={{ borderColor: "var(--border)", color: "var(--muted)" }}>
          No signal data available for this case.
        </p>
      )}
    </Link>
  );
}
