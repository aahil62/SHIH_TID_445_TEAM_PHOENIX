import Link from "next/link";
import { getRecentTransactions } from "@/lib/api";
import DecisionBadge from "@/components/DecisionBadge";
import { formatAmount, formatScore, formatTimestamp, DECISION_TONE } from "@/lib/risk";
import { plainReason } from "@/lib/reasons";

export default async function FeedPage() {
  const { transactions } = await getRecentTransactions(25);
  const sorted = [...transactions].sort((a, b) => b.final_score - a.final_score);

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <div className="mb-5 flex items-baseline justify-between">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Alert Feed
        </h1>
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          {sorted.length} recent transactions, highest risk first
        </span>
      </div>

      <div
        className="overflow-x-auto rounded-[var(--radius-panel)] border"
        style={{
          borderColor: "var(--border)",
          backgroundColor: "var(--panel)",
          boxShadow: "var(--shadow-panel)",
        }}
      >
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr
              className="border-b text-left text-[11px] uppercase tracking-wider"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            >
              <th className="px-4 py-2.5 font-semibold">Transaction</th>
              <th className="px-4 py-2.5 font-semibold">Amount</th>
              <th className="px-4 py-2.5 font-semibold">Merchant</th>
              <th className="px-4 py-2.5 font-semibold">Risk</th>
              <th className="px-4 py-2.5 font-semibold">Status</th>
              <th className="px-4 py-2.5 font-semibold">Why</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((txn) => {
              const tone = DECISION_TONE[txn.decision];
              return (
                <tr
                  key={txn.txn_id}
                  className="border-b transition-colors last:border-b-0 hover:bg-black/5 dark:hover:bg-white/5"
                  style={{ borderColor: "var(--border)", borderLeft: `3px solid ${tone.fg}` }}
                >
                  <td className="px-4 py-3 align-top">
                    <Link
                      href={`/case?txn_id=${encodeURIComponent(txn.txn_id)}`}
                      className="rounded-sm font-mono text-xs font-medium hover:underline"
                      style={{ color: "var(--cobalt)" }}
                    >
                      {txn.txn_id}
                    </Link>
                    <div className="font-mono text-[11px]" style={{ color: "var(--muted)" }}>
                      {txn.account_id}
                    </div>
                  </td>
                  <td className="px-4 py-3 align-top font-mono text-xs">
                    {formatAmount(txn.amount)}
                  </td>
                  <td className="px-4 py-3 align-top capitalize">
                    {txn.merchant_category.replace(/_/g, " ")}
                  </td>
                  <td className="px-4 py-3 align-top font-mono text-xs font-medium">
                    {formatScore(txn.final_score)}
                  </td>
                  <td className="px-4 py-3 align-top">
                    <DecisionBadge decision={txn.decision} />
                  </td>
                  <td className="px-4 py-3 align-top text-xs" style={{ color: "var(--foreground)" }}>
                    {plainReason(txn.top_reason)}
                    <div className="mt-0.5 text-[11px]" style={{ color: "var(--muted)" }}>
                      {formatTimestamp(txn.timestamp)}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
