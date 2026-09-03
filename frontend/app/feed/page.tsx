import Link from "next/link";
import { getRecentTransactions } from "@/lib/api";
import DecisionBadge from "@/components/DecisionBadge";
import { formatAmount, formatScore, formatTimestamp } from "@/lib/risk";
import { plainReason } from "@/lib/reasons";

export default async function FeedPage() {
  const { transactions } = await getRecentTransactions(25);
  const sorted = [...transactions].sort((a, b) => b.final_score - a.final_score);

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <div className="mb-4 flex items-baseline justify-between">
        <h1 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>
          Alert Feed
        </h1>
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          {sorted.length} recent transactions, highest risk first
        </span>
      </div>

      <div
        className="overflow-x-auto rounded-lg border"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
      >
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr
              className="border-b text-left text-xs uppercase tracking-wide"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            >
              <th className="px-4 py-2 font-medium">Transaction</th>
              <th className="px-4 py-2 font-medium">Amount</th>
              <th className="px-4 py-2 font-medium">Merchant</th>
              <th className="px-4 py-2 font-medium">Risk</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Why</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((txn) => (
              <tr
                key={txn.txn_id}
                className="border-b last:border-b-0"
                style={{ borderColor: "var(--border)" }}
              >
                <td className="px-4 py-3 align-top">
                  <Link
                    href={`/case?txn_id=${encodeURIComponent(txn.txn_id)}`}
                    className="font-mono text-xs hover:underline"
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
                <td className="px-4 py-3 align-top font-mono text-xs">
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
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
