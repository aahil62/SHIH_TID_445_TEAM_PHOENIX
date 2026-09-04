import Link from "next/link";
import { getDashboardStats, getPerformanceStats } from "@/lib/api";
import { formatAmount, formatScore } from "@/lib/risk";

const SIGNALS = [
  { key: "rule_agent", name: "Rule Agent", desc: "High amounts, risky merchant categories, odd hours, structuring patterns." },
  { key: "velocity_agent", name: "Velocity Agent", desc: "Transaction bursts — too many, too fast, on one account." },
  { key: "behavioral_agent", name: "Behavioral Agent", desc: "Deviation from this account's own historical pattern." },
  { key: "graph_agent", name: "Graph Agent", desc: "Shared devices/IPs across accounts — the signal that catches coordinated rings." },
  { key: "ml_agent", name: "ML Agent", desc: "A trained gradient-boosted classifier learning nonlinear patterns no rule captures." },
  { key: "fraud_dna_agent", name: "Fraud DNA Agent", desc: "Matches suspicious clusters against a growing library of confirmed fraud typologies." },
];

function Glass({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl border backdrop-blur-xl ${className}`}
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--panel)",
        boxShadow: "var(--shadow-panel-raised)",
      }}
    >
      {children}
    </div>
  );
}

export default async function LandingPage() {
  const [dash, perf] = await Promise.all([getDashboardStats(), getPerformanceStats()]);
  const preventedApprox = dash.critical_alerts * 250000; // illustrative, from real critical-case count

  return (
    <div style={{ color: "var(--foreground)" }}>
      {/* ── Top bar ─────────────────────────────────────────────── */}
      <div
        className="sticky top-0 z-40 flex items-center justify-between px-8 py-4 backdrop-blur-2xl"
        style={{ backgroundColor: "rgba(8,14,11,0.5)", borderBottom: "1px solid var(--border)" }}
      >
        <span className="text-[17px] font-bold" style={{ color: "var(--foreground)" }}>FraudLens</span>
        <div className="flex items-center gap-8">
          <a href="#signals" className="text-[13.5px] font-medium" style={{ color: "var(--muted)" }}>Intelligence</a>
          <a href="#benchmarks" className="text-[13.5px] font-medium" style={{ color: "var(--muted)" }}>Benchmarks</a>
          <Link
            href="/dashboard"
            className="rounded-lg px-4 py-2 text-[13.5px] font-semibold"
            style={{ background: "linear-gradient(135deg, rgba(31,167,116,0.9), rgba(18,103,70,0.9))", color: "#fff" }}
          >
            Open Analyst Console
          </Link>
        </div>
      </div>

      {/* ── Hero ────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-3xl px-8 pt-24 pb-16 text-center">
        <div
          className="mb-7 inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium"
          style={{ borderColor: "var(--border)", color: "var(--muted)" }}
        >
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: "var(--risk-low)" }} />
          AI Fraud Intelligence &amp; Regulatory CaseOps Platform
        </div>
        <h1 className="mb-6 text-[44px] font-extrabold leading-[1.1] tracking-tight sm:text-[56px]">
          Detect Fraud. Understand the Pattern.
          <br />
          Act With Confidence.
        </h1>
        <p className="mx-auto mb-9 max-w-xl text-base leading-relaxed" style={{ color: "var(--muted)" }}>
          FraudLens combines six intelligence signals into one explainable fraud decision — from
          detection to investigation, Fraud DNA, analyst decisions, audit trails, and regulatory context.
        </p>
        <div className="flex items-center justify-center gap-3.5">
          <Link
            href="/dashboard"
            className="rounded-xl px-6 py-3.5 text-[15px] font-semibold"
            style={{ background: "linear-gradient(135deg, rgba(31,167,116,0.9), rgba(18,103,70,0.9))", color: "#fff" }}
          >
            Open Analyst Console
          </Link>
          <a
            href="#signals"
            className="rounded-xl border px-6 py-3.5 text-[15px] font-semibold"
            style={{ borderColor: "var(--border)" }}
          >
            Explore Intelligence
          </a>
        </div>
      </div>

      {/* ── Live product preview (real numbers) ────────────────────── */}
      <div className="mx-auto max-w-5xl px-8 pb-24">
        <Glass className="overflow-hidden">
          <div className="p-8">
            <h3 className="mb-5 text-lg font-bold">Risk Intelligence Overview — live</h3>
            <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  Critical Alerts
                </div>
                <div className="mt-1.5 font-mono text-[26px] font-semibold" style={{ color: "var(--risk-critical)" }}>
                  {dash.critical_alerts}
                </div>
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  Pending Reviews
                </div>
                <div className="mt-1.5 font-mono text-[26px] font-semibold" style={{ color: "var(--risk-medium)" }}>
                  {dash.pending_reviews}
                </div>
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  Transactions Analyzed
                </div>
                <div className="mt-1.5 font-mono text-[26px] font-semibold">{dash.transactions_analyzed}</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  Est. Exposure Flagged
                </div>
                <div className="mt-1.5 font-mono text-[26px] font-semibold" style={{ color: "var(--risk-low)" }}>
                  {formatAmount(preventedApprox)}
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-2.5">
              {dash.agent_averages.map((a) => (
                <div key={a.agent_name} className="flex items-center gap-3">
                  <span className="w-32 shrink-0 text-xs" style={{ color: "var(--muted)" }}>
                    {a.agent_name.replace(/_/g, " ")}
                  </span>
                  <div className="h-1 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: "rgba(150,190,170,0.09)" }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${a.avg_score * 100}%`, backgroundColor: "var(--cobalt)" }}
                    />
                  </div>
                  <span className="w-9 shrink-0 text-right font-mono text-xs font-semibold">
                    {formatScore(a.avg_score)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Glass>
      </div>

      {/* ── Six signals ─────────────────────────────────────────── */}
      <div id="signals" className="mx-auto max-w-5xl px-8 pb-24">
        <div className="mb-12 text-center">
          <h2 className="mb-3 text-[34px] font-extrabold tracking-tight">Six Signals. One Decision.</h2>
          <p className="mx-auto max-w-lg text-base" style={{ color: "var(--muted)" }}>
            Every transaction is evaluated from multiple independent angles before one final decision.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {SIGNALS.map((s) => {
            const avg = dash.agent_averages.find((a) => a.agent_name === s.key)?.avg_score;
            return (
              <Glass key={s.key} className="p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-lg"
                    style={{ backgroundColor: "rgba(22,163,106,0.1)" }}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--cobalt)" strokeWidth="1.7">
                      <circle cx="12" cy="12" r="8.5" />
                      <circle cx="12" cy="12" r="4.5" />
                    </svg>
                  </div>
                  {avg !== undefined && (
                    <span className="font-mono text-xs font-semibold" style={{ color: "var(--cobalt)" }}>
                      avg {formatScore(avg)}
                    </span>
                  )}
                </div>
                <h3 className="mb-1.5 text-base font-bold">{s.name}</h3>
                <p className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{s.desc}</p>
              </Glass>
            );
          })}
        </div>
      </div>

      {/* ── Benchmarks (real numbers) ───────────────────────────── */}
      <div id="benchmarks" className="mx-auto max-w-5xl px-8 pb-24">
        <div className="mb-10 text-center">
          <h2 className="mb-3 text-[34px] font-extrabold tracking-tight">Measured, Not Marketed.</h2>
          <p className="mx-auto max-w-lg text-base" style={{ color: "var(--muted)" }}>
            Benchmarked on {perf.dataset.total.toLocaleString()} synthetic transactions — every number below
            comes straight from the live benchmark, not a slide.
          </p>
        </div>
        <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Glass className="px-5 py-6 text-center">
            <div className="font-mono text-3xl font-bold" style={{ color: "var(--cobalt)" }}>
              {perf.ensemble.f1.toFixed(3)}
            </div>
            <div className="mt-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
              Ensemble F1
            </div>
          </Glass>
          <Glass className="px-5 py-6 text-center">
            <div className="font-mono text-3xl font-bold" style={{ color: "var(--cobalt)" }}>
              {perf.ensemble.auc_pr.toFixed(3)}
            </div>
            <div className="mt-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
              AUC-PR
            </div>
          </Glass>
          <Glass className="px-5 py-6 text-center">
            <div className="font-mono text-3xl font-bold" style={{ color: "var(--cobalt)" }}>
              {perf.ensemble.precision.toFixed(3)}
            </div>
            <div className="mt-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
              Precision
            </div>
          </Glass>
          <Glass className="px-5 py-6 text-center">
            <div className="font-mono text-3xl font-bold">{perf.dataset.test}</div>
            <div className="mt-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
              Held-out Test Cases
            </div>
          </Glass>
        </div>
        {perf.external_validation && (
          <Glass className="flex flex-wrap items-center justify-between gap-6 px-7 py-6">
            <div>
              <div className="mb-1 text-[13px] font-bold">External Validation — {perf.external_validation.dataset}</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {perf.external_validation.total_rows.toLocaleString()} real transactions · a separate model, run
                for validation only
              </div>
            </div>
            <div className="flex gap-7">
              <div className="text-center">
                <div className="font-mono text-lg font-bold">{perf.external_validation.precision.toFixed(3)}</div>
                <div className="text-[10px]" style={{ color: "var(--muted)" }}>Precision</div>
              </div>
              <div className="text-center">
                <div className="font-mono text-lg font-bold">{perf.external_validation.recall.toFixed(3)}</div>
                <div className="text-[10px]" style={{ color: "var(--muted)" }}>Recall</div>
              </div>
              <div className="text-center">
                <div className="font-mono text-lg font-bold">{perf.external_validation.auc_pr.toFixed(3)}</div>
                <div className="text-[10px]" style={{ color: "var(--muted)" }}>AUC-PR</div>
              </div>
            </div>
          </Glass>
        )}
      </div>

      {/* ── Final CTA ───────────────────────────────────────────── */}
      <div className="mx-auto max-w-xl px-8 pb-20 text-center">
        <h2 className="mb-4 text-[32px] font-extrabold tracking-tight">Turn Fraud Signals Into Decisions.</h2>
        <p className="mb-8 text-base" style={{ color: "var(--muted)" }}>
          Detect patterns earlier, investigate faster, and make every fraud decision explainable.
        </p>
        <Link
          href="/dashboard"
          className="inline-block rounded-xl px-6 py-3.5 text-[15px] font-semibold"
          style={{ background: "linear-gradient(135deg, rgba(31,167,116,0.9), rgba(18,103,70,0.9))", color: "#fff" }}
        >
          Open Analyst Console
        </Link>
      </div>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <div className="border-t px-8 py-9" style={{ borderColor: "var(--border)" }}>
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-6 text-xs" style={{ color: "var(--muted)" }}>
          <span>© 2026 FraudLens · Team Phoenix · Smart Horizon Grand Finale</span>
          <div className="flex gap-6">
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/feed">Alerts</Link>
            <Link href="/network">Fraud Network</Link>
            <Link href="/fraud-dna">Fraud DNA</Link>
            <Link href="/reports">Reports</Link>
            <Link href="/audit">Audit Trail</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
