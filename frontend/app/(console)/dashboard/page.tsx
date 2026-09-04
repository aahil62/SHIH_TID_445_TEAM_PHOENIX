import Link from "next/link";
import { getDashboardStats, getRecentTransactions } from "@/lib/api";
import Panel from "@/components/Panel";
import StatCard from "@/components/StatCard";
import { formatAgentName } from "@/lib/agents";
import { DECISION_TONE, formatScore } from "@/lib/risk";
import type { Decision } from "@/lib/types";

export default async function DashboardPage() {
  const [stats, feed] = await Promise.all([
    getDashboardStats(),
    getRecentTransactions(6),
  ]);

  const maxAvg = Math.max(0.01, ...stats.agent_averages.map((a) => a.avg_score));

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Risk Intelligence
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
          Real-time overview of fraud risk, alerts and investigations — {stats.transactions_analyzed}{" "}
          transactions analyzed.
        </p>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Critical Alerts" value={stats.critical_alerts} color="var(--risk-critical)" href="/feed" />
        <StatCard label="Pending Reviews" value={stats.pending_reviews} color="var(--risk-medium)" href="/feed" />
        <StatCard label="Blocked Transactions" value={stats.blocked_transactions} href="/reports" />
        <StatCard label="Investigations" value={stats.investigations} href="/cases" />
        <StatCard label="Fraud Rings" value={stats.fraud_rings} color="var(--amber)" href="/network" />
        <StatCard label="Accounts Restricted" value={stats.restricted_accounts} color="var(--amber)" />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[1.7fr_1fr]">
        <Panel title="Risk Trend (by day)">
          {stats.risk_trend.length > 0 ? (
            <div className="flex items-end gap-1.5" style={{ height: 140 }}>
              {stats.risk_trend.map((point) => (
                <div key={point.date} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t"
                    style={{
                      height: `${Math.max(4, point.avg_score * 120)}px`,
                      backgroundColor: "var(--cobalt)",
                      opacity: 0.85,
                    }}
                    title={`${point.date}: ${formatScore(point.avg_score)} avg risk, ${point.count} txns`}
                  />
                  <span className="text-[9px]" style={{ color: "var(--muted)" }}>
                    {point.date.slice(5)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>No trend data yet.</p>
          )}
        </Panel>

        <Panel title="Agent Performance">
          <div className="flex flex-col gap-3">
            {stats.agent_averages.map((a) => (
              <div key={a.agent_name} className="flex items-center gap-2.5">
                <span className="w-24 shrink-0 text-xs" style={{ color: "var(--muted)" }}>
                  {formatAgentName(a.agent_name)}
                </span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: "rgba(150,190,170,0.09)" }}>
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${(a.avg_score / maxAvg) * 100}%`, backgroundColor: "var(--cobalt)" }}
                  />
                </div>
                <span className="w-9 shrink-0 text-right font-mono text-xs font-semibold" style={{ color: "var(--foreground)" }}>
                  {formatScore(a.avg_score)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel title="Recent Alerts">
        <div className="mb-3 flex justify-end">
          <Link href="/feed" className="text-xs font-semibold" style={{ color: "var(--cobalt)" }}>
            View all →
          </Link>
        </div>
        <div className="flex flex-col gap-1">
          {feed.transactions.map((t) => {
            const tone = DECISION_TONE[t.decision as Decision];
            return (
              <Link
                key={t.txn_id}
                href={`/case?txn_id=${encodeURIComponent(t.txn_id)}`}
                className="hoverable-row flex items-center gap-3 rounded-[var(--radius-control)] px-2 py-2 transition-colors"
                style={{ borderColor: "transparent" }}
              >
                <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: tone.fg }} />
                <span className="w-40 shrink-0 truncate font-mono text-xs" style={{ color: "var(--muted)" }}>
                  {t.txn_id}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm" style={{ color: "var(--foreground)" }}>
                  {t.top_reason || "No specific risk factors flagged"}
                </span>
                <span className="shrink-0 font-mono text-xs font-semibold" style={{ color: tone.fg }}>
                  {formatScore(t.final_score)}
                </span>
              </Link>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
