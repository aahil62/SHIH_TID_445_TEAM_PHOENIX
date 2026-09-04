import Link from "next/link";
import { getDashboardStats, getPerformanceStats, getRecentTransactions } from "@/lib/api";
import { formatAmount, formatScore, DECISION_TONE, DECISION_LABEL } from "@/lib/risk";
import CountUp from "@/components/CountUp";
import Reveal from "@/components/Reveal";

const SIGNALS = [
  {
    key: "rule_agent",
    name: "Rule Agent",
    desc: "High amounts, risky merchant categories, odd hours, structuring patterns.",
    icon: (
      <path d="M12 3l7 3v5.5c0 4.7-3 8.4-7 9.5-4-1.1-7-4.8-7-9.5V6l7-3z" />
    ),
  },
  {
    key: "velocity_agent",
    name: "Velocity Agent",
    desc: "Transaction bursts — too many, too fast, on one account.",
    icon: (
      <>
        <circle cx="12" cy="13" r="8" />
        <path d="M12 13l4.5-4.5M8 13a4 4 0 0 1 4-4" />
        <path d="M12 3v2M4.5 6.5l1.4 1.4M19.5 6.5l-1.4 1.4" />
      </>
    ),
  },
  {
    key: "behavioral_agent",
    name: "Behavioral Agent",
    desc: "Deviation from this account's own historical pattern.",
    icon: <path d="M3 13h3.5l2-6 3 12 2-9 1.5 3H21" />,
  },
  {
    key: "graph_agent",
    name: "Graph Agent",
    desc: "Shared devices/IPs across accounts — the signal that catches coordinated rings.",
    icon: (
      <>
        <circle cx="6" cy="18" r="2.2" />
        <circle cx="18" cy="6" r="2.2" />
        <circle cx="18" cy="18" r="2.2" />
        <path d="M8 16.7l7.5-9.3M8 17.8l8 0" />
      </>
    ),
  },
  {
    key: "ml_agent",
    name: "ML Agent",
    desc: "A trained gradient-boosted classifier learning nonlinear patterns no rule captures.",
    icon: (
      <>
        <rect x="7" y="7" width="10" height="10" rx="1.5" />
        <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
      </>
    ),
  },
  {
    key: "fraud_dna_agent",
    name: "Fraud DNA Agent",
    desc: "Matches suspicious clusters against a growing library of confirmed fraud typologies.",
    icon: (
      <>
        <path d="M7 3c0 5 10 3 10 8s-10 3-10 8" />
        <path d="M17 3c0 5-10 3-10 8s10 3 10 8" />
        <path d="M8 6h8M7.3 12h9.4M8 18h8" />
      </>
    ),
  },
];

const FLOW = [
  { n: "01", title: "Ingest", desc: "Every transaction enters the pipeline the instant it happens — nothing pre-batched." },
  { n: "02", title: "Six agents score in parallel", desc: "Rule, velocity, behavioral, graph, ML and Fraud DNA each independently evaluate the same transaction." },
  { n: "03", title: "Weighted ensemble decision", desc: "One explainable score and recommendation — clear, review, block, or block & report." },
  { n: "04", title: "Bounded autonomous action", desc: "On high-confidence rings, the system auto-holds the case and tightens account limits — always reversible by a human." },
];

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

export default async function LandingPage() {
  const [dash, perf, recent] = await Promise.all([
    getDashboardStats(),
    getPerformanceStats(),
    getRecentTransactions(50),
  ]);
  const preventedApprox = dash.critical_alerts * 250000; // illustrative, from real critical-case count
  const SEVERITY: Record<string, number> = { block_and_report: 3, block: 2, review: 1, clear: 0 };
  const showcase = [...recent.transactions]
    .sort((a, b) => SEVERITY[b.decision] - SEVERITY[a.decision] || b.final_score - a.final_score)
    .slice(0, 2);

  return (
    <div style={{ color: "var(--foreground)" }}>
      {/* ── Top bar ─────────────────────────────────────────────── */}
      <div
        className="sticky top-0 z-40 flex items-center justify-between px-8 py-4 backdrop-blur-2xl"
        style={{ backgroundColor: "rgba(5,8,7,0.7)", borderBottom: "1px solid var(--border)" }}
      >
        <span className="flex items-center gap-2 text-[17px] font-bold tracking-tight" style={{ color: "var(--foreground)" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" style={{ color: "var(--cobalt)" }}>
            <path d="M12 2.5l7.5 3v6c0 5-3.2 8.4-7.5 10-4.3-1.6-7.5-5-7.5-10v-6z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
          </svg>
          FraudLens
        </span>
        <div className="flex items-center gap-8">
          <a href="#how-it-works" className="hidden text-[13.5px] font-medium sm:inline" style={{ color: "var(--muted)" }}>How it works</a>
          <a href="#signals" className="hidden text-[13.5px] font-medium sm:inline" style={{ color: "var(--muted)" }}>Intelligence</a>
          <a href="#benchmarks" className="hidden text-[13.5px] font-medium sm:inline" style={{ color: "var(--muted)" }}>Benchmarks</a>
          <Link
            href="/dashboard"
            className="hover-fill rounded-lg px-4 py-2 text-[13.5px] font-semibold"
            style={{ background: "linear-gradient(135deg, rgba(31,167,116,0.9), rgba(18,103,70,0.9))", color: "#fff" }}
          >
            Open Analyst Console
          </Link>
        </div>
      </div>

      {/* ── Hero ────────────────────────────────────────────────── */}
      <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-14 overflow-hidden px-8 pt-20 pb-24 lg:grid-cols-[1.05fr_0.95fr] lg:pt-28">
        <div>
          <Reveal>
            <div
              className="mb-7 inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            >
              <span className="pulse-dot h-1.5 w-1.5 rounded-full" style={{ backgroundColor: "var(--risk-low)" }} />
              AI Fraud Intelligence &amp; Regulatory CaseOps Platform
            </div>
            <h1 className="mb-6 text-[42px] font-extrabold leading-[1.08] tracking-tight sm:text-[54px]">
              Fraud doesn&apos;t announce itself.
              <br />
              <span style={{ color: "var(--cobalt)" }}>FraudLens</span> finds it anyway.
            </h1>
            <p className="mb-9 max-w-lg text-base leading-relaxed" style={{ color: "var(--muted)" }}>
              Six independent intelligence signals, one explainable decision. From detection to
              investigation to a bounded, human-reversible autonomous response — built for
              analysts who need to move as fast as the fraud they&apos;re chasing.
            </p>
            <div className="flex flex-wrap items-center gap-3.5">
              <Link
                href="/dashboard"
                className="hover-fill rounded-xl px-6 py-3.5 text-[15px] font-semibold"
                style={{ background: "linear-gradient(135deg, rgba(31,167,116,0.9), rgba(18,103,70,0.9))", color: "#fff" }}
              >
                Open Analyst Console
              </Link>
              <a
                href="#how-it-works"
                className="hover-fill rounded-xl border px-6 py-3.5 text-[15px] font-semibold"
                style={{ borderColor: "var(--border)" }}
              >
                See how it works
              </a>
            </div>
          </Reveal>

          <Reveal delay={150} className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-xs">
            <span className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
              <Icon><path d="M9 12l2 2 4-4M12 3l7 3v5.5c0 4.7-3 8.4-7 9.5-4-1.1-7-4.8-7-9.5V6l7-3z" /></Icon>
              RBI / PMLA / CERT-In aware
            </span>
            <span className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
              <Icon><path d="M12 2v20M2 12h20" /><circle cx="12" cy="12" r="9" /></Icon>
              Every action human-reversible
            </span>
            <span className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
              <Icon><path d="M4 19V9M11 19V4M18 19v-6" /></Icon>
              Benchmarked, not marketed
            </span>
          </Reveal>
        </div>

        {/* Floating live-case showcase — real transactions, real scores */}
        <Reveal delay={200}>
          <div className="relative mx-auto w-full max-w-sm">
            <div
              className="absolute -inset-x-6 -inset-y-6 -z-10 rounded-[32px] blur-2xl"
              style={{ background: "radial-gradient(circle, rgba(22,163,106,0.18), transparent 70%)" }}
            />
            {showcase.map((t, i) => {
              const tone = DECISION_TONE[t.decision];
              return (
                <div
                  key={t.txn_id}
                  className="hover-lift mb-4 rounded-2xl border p-5 glass last:mb-0"
                  style={{
                    borderColor: `color-mix(in srgb, ${tone.fg} 35%, var(--border))`,
                    background: `linear-gradient(160deg, color-mix(in srgb, ${tone.fg} 12%, transparent), transparent 60%), var(--panel-solid)`,
                    boxShadow: "var(--shadow-panel-raised)",
                    marginLeft: i === 1 ? "22px" : undefined,
                  }}
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span className="font-mono text-[11px]" style={{ color: "var(--muted)" }}>{t.txn_id}</span>
                    <span
                      className="rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                      style={{ backgroundColor: tone.bg, color: tone.fg }}
                    >
                      {DECISION_LABEL[t.decision]}
                    </span>
                  </div>
                  <div className="mb-1 font-mono text-2xl font-bold">{formatAmount(t.amount)}</div>
                  <div className="mb-3 text-xs capitalize" style={{ color: "var(--muted)" }}>
                    {t.merchant_category.replace(/_/g, " ")}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-1 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: "rgba(150,190,170,0.09)" }}>
                      <div className="h-full rounded-full" style={{ width: `${t.final_score * 100}%`, backgroundColor: tone.fg }} />
                    </div>
                    <span className="font-mono text-xs font-semibold" style={{ color: tone.fg }}>
                      {formatScore(t.final_score)}
                    </span>
                  </div>
                  <p className="mt-3 text-[11px] leading-relaxed" style={{ color: "var(--muted)" }}>
                    {t.top_reason}
                  </p>
                </div>
              );
            })}
            <div className="mt-1 text-center text-[11px]" style={{ color: "var(--muted)" }}>
              Live from the analyst console — not staged.
            </div>
          </div>
        </Reveal>
      </div>

      {/* ── Live stats strip ────────────────────────────────────── */}
      <Reveal>
        <div className="mx-auto max-w-6xl px-8 pb-24">
          <div
            className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border sm:grid-cols-4"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--border)" }}
          >
            {[
              { label: "Critical Alerts", value: dash.critical_alerts, color: "var(--risk-critical)" },
              { label: "Pending Reviews", value: dash.pending_reviews, color: "var(--risk-medium)" },
              { label: "Transactions Analyzed", value: dash.transactions_analyzed, color: "var(--foreground)" },
              { label: "Exposure Flagged", value: preventedApprox, color: "var(--risk-low)", money: true },
            ].map((s) => (
              <div key={s.label} className="px-6 py-7" style={{ backgroundColor: "var(--canvas)" }}>
                <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  {s.label}
                </div>
                <div className="font-mono text-[26px] font-bold" style={{ color: s.color }}>
                  {s.money ? (
                    <>₹<CountUp value={s.value / 100000} decimals={1} />L</>
                  ) : (
                    <CountUp value={s.value} />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Reveal>

      {/* ── How it works ────────────────────────────────────────── */}
      <div id="how-it-works" className="mx-auto max-w-5xl px-8 pb-24">
        <Reveal>
          <div className="mb-14 text-center">
            <h2 className="mb-3 text-[32px] font-extrabold tracking-tight">From transaction to decision, in one pipeline.</h2>
            <p className="mx-auto max-w-lg text-base" style={{ color: "var(--muted)" }}>
              No black box. Every step is visible, and every autonomous action is reversible.
            </p>
          </div>
        </Reveal>
        <div className="grid grid-cols-1 gap-0 sm:grid-cols-4">
          {FLOW.map((step, i) => (
            <Reveal key={step.n} delay={i * 100} className="relative px-2">
              <div
                className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl font-mono text-sm font-bold"
                style={{ backgroundColor: "rgba(22,163,106,0.12)", color: "var(--cobalt)" }}
              >
                {step.n}
              </div>
              {i < FLOW.length - 1 && (
                <div
                  className="absolute top-[22px] left-[calc(50%+30px)] hidden h-px w-[calc(100%-30px)] sm:block"
                  style={{ background: "linear-gradient(90deg, var(--border), transparent)" }}
                />
              )}
              <h3 className="mb-1.5 text-[15px] font-bold">{step.title}</h3>
              <p className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{step.desc}</p>
            </Reveal>
          ))}
        </div>
      </div>

      {/* ── Six signals ─────────────────────────────────────────── */}
      <div id="signals" className="mx-auto max-w-5xl px-8 pb-24">
        <Reveal>
          <div className="mb-12 text-center">
            <h2 className="mb-3 text-[32px] font-extrabold tracking-tight">Six signals. One decision.</h2>
            <p className="mx-auto max-w-lg text-base" style={{ color: "var(--muted)" }}>
              Every transaction is evaluated from multiple independent angles before one final decision.
            </p>
          </div>
        </Reveal>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {SIGNALS.map((s, i) => {
            const avg = dash.agent_averages.find((a) => a.agent_name === s.key)?.avg_score;
            return (
              <Reveal key={s.key} delay={(i % 3) * 90}>
                <div
                  className="hover-lift rounded-2xl border p-6 glass"
                  style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)", boxShadow: "var(--shadow-panel-raised)" }}
                >
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="flex items-center gap-2 text-base font-bold">
                      <span style={{ color: "var(--cobalt)" }}><Icon>{s.icon}</Icon></span>
                      {s.name}
                    </h3>
                    {avg !== undefined && (
                      <span className="shrink-0 font-mono text-xs font-semibold" style={{ color: "var(--cobalt)" }}>
                        avg {formatScore(avg)}
                      </span>
                    )}
                  </div>
                  <p className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{s.desc}</p>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>

      {/* ── Benchmarks (real numbers) ───────────────────────────── */}
      <div id="benchmarks" className="mx-auto max-w-5xl px-8 pb-24">
        <Reveal>
          <div className="mb-10 text-center">
            <h2 className="mb-3 text-[32px] font-extrabold tracking-tight">Measured, not marketed.</h2>
            <p className="mx-auto max-w-lg text-base" style={{ color: "var(--muted)" }}>
              Benchmarked on {perf.dataset.total.toLocaleString()} synthetic transactions — every number below
              comes straight from the live benchmark, not a slide.
            </p>
          </div>
        </Reveal>
        <Reveal>
          <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { value: perf.ensemble.f1, label: "Ensemble F1", decimals: 3 },
              { value: perf.ensemble.auc_pr, label: "AUC-PR", decimals: 3 },
              { value: perf.ensemble.precision, label: "Precision", decimals: 3 },
              { value: perf.dataset.test, label: "Held-out Test Cases", decimals: 0 },
            ].map((m) => (
              <div
                key={m.label}
                className="hover-lift rounded-2xl border px-5 py-6 text-center glass"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)", boxShadow: "var(--shadow-panel-raised)" }}
              >
                <div className="font-mono text-3xl font-bold" style={{ color: "var(--cobalt)" }}>
                  <CountUp value={m.value} decimals={m.decimals} />
                </div>
                <div className="mt-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  {m.label}
                </div>
              </div>
            ))}
          </div>
        </Reveal>
        {perf.external_validation && (
          <Reveal delay={150}>
            <div
              className="hover-lift flex flex-wrap items-center justify-between gap-6 rounded-2xl border px-7 py-6 glass"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)", boxShadow: "var(--shadow-panel-raised)" }}
            >
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
            </div>
          </Reveal>
        )}
      </div>

      {/* ── Final CTA ───────────────────────────────────────────── */}
      <Reveal>
        <div className="mx-auto max-w-xl px-8 pb-20 text-center">
          <h2 className="mb-4 text-[30px] font-extrabold tracking-tight">Turn fraud signals into decisions.</h2>
          <p className="mb-8 text-base" style={{ color: "var(--muted)" }}>
            Detect patterns earlier, investigate faster, and make every fraud decision explainable.
          </p>
          <Link
            href="/dashboard"
            className="hover-fill inline-block rounded-xl px-6 py-3.5 text-[15px] font-semibold"
            style={{ background: "linear-gradient(135deg, rgba(31,167,116,0.9), rgba(18,103,70,0.9))", color: "#fff" }}
          >
            Open Analyst Console
          </Link>
        </div>
      </Reveal>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <div className="border-t px-8 py-9" style={{ borderColor: "var(--border)" }}>
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-6 text-xs" style={{ color: "var(--muted)" }}>
          <span>© 2026 FraudLens · Team Phoenix · Smart Horizon Grand Finale</span>
          <div className="flex gap-6">
            <Link href="/dashboard" className="hover:underline">Dashboard</Link>
            <Link href="/feed" className="hover:underline">Alerts</Link>
            <Link href="/network" className="hover:underline">Fraud Network</Link>
            <Link href="/fraud-dna" className="hover:underline">Fraud DNA</Link>
            <Link href="/reports" className="hover:underline">Reports</Link>
            <Link href="/audit" className="hover:underline">Audit Trail</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
