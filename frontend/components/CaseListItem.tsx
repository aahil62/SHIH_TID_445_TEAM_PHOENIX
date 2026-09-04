import Link from "next/link";
import type { Case } from "@/lib/types";
import { formatAmount, formatTimestamp, DECISION_TONE } from "@/lib/risk";
import { RISK_TIER_LABEL } from "@/lib/tier";
import MaskedId from "./MaskedId";
import SignalIcons from "./SignalIcons";

/** One card in the investigation feed / case list — real tier, amount,
 * masked account, and a compact icon per real agent_scores entry (see
 * SignalIcons — full per-agent detail lives on the case page, not
 * repeated here for every row in a list). */
export default function CaseListItem({ item }: { item: Case }) {
  const tone = DECISION_TONE[item.decision];

  return (
    <Link
      href={`/case?txn_id=${encodeURIComponent(item.txn_id)}`}
      className="block rounded-[var(--radius-panel)] border px-4 py-3.5 shadow-[var(--shadow-panel)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[var(--shadow-panel-raised)]"
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--panel)",
        borderLeft: `3px solid ${tone.fg}`,
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className="rounded-[var(--radius-control)] px-2 py-0.5 text-[11px] font-bold tracking-wide"
            style={{ color: tone.fg, backgroundColor: tone.bg }}
          >
            {RISK_TIER_LABEL[item.decision]}
          </span>
          <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
            {item.txn_id}
          </span>
        </div>
        <SignalIcons scores={item.agent_scores} />
      </div>

      <div className="mt-2.5 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
        <span className="font-mono text-base font-semibold">{formatAmount(item.transaction.amount)}</span>
        <span style={{ color: "var(--muted)" }}>
          Account <MaskedId value={item.transaction.account_id} />
        </span>
        <span className="text-xs capitalize" style={{ color: "var(--muted)" }}>
          {item.transaction.merchant_category.replace(/_/g, " ")}
        </span>
        <span className="ml-auto text-[11px]" style={{ color: "var(--muted)" }}>
          {formatTimestamp(item.transaction.timestamp)}
        </span>
      </div>
    </Link>
  );
}
