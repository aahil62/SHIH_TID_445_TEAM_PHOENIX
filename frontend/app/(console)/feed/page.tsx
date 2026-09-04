import { getRecentTransactions, getCases } from "@/lib/api";
import CaseListItem from "@/components/CaseListItem";
import type { Case } from "@/lib/types";

export default async function FeedPage() {
  // Two real calls, sequential on purpose: /transactions/recent's handler
  // analyzes each of the top-N transactions as a side effect, which is
  // what guarantees /cases (called second) actually has full agent_scores
  // for those same transactions — even on a cold server with nothing
  // analyzed yet. See DESIGN-AUDIT.md's 2026-09-04 addendum, Finding A.
  const { transactions } = await getRecentTransactions(25);
  const { cases } = await getCases();
  const caseByTxnId = new Map(cases.map((c) => [c.txn_id, c]));

  const items: Case[] = transactions
    .map((t) => caseByTxnId.get(t.txn_id))
    .filter((c): c is Case => c !== undefined)
    .sort((a, b) => b.final_score - a.final_score);

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <div className="mb-5 flex items-baseline justify-between">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Alert Feed
        </h1>
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          {items.length} recent alert{items.length === 1 ? "" : "s"}, highest risk first
        </span>
      </div>

      {items.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>No alerts available.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <CaseListItem key={item.txn_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
