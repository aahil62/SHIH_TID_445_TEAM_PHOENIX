import { getCases, getCaseGraph } from "@/lib/api";
import Panel from "@/components/Panel";
import FraudRingGraph from "@/components/FraudRingGraph";
import AnimatedNumber from "@/components/AnimatedNumber";
import type { Case, CaseGraph } from "@/lib/types";

function computeStats(cases: Case[]) {
  let clear = 0;
  let review = 0;
  let block = 0;
  let blockAndReport = 0;
  let ringCount = 0;
  let dnaMatchCount = 0;

  for (const c of cases) {
    if (c.decision === "clear") clear += 1;
    else if (c.decision === "review") review += 1;
    else if (c.decision === "block") block += 1;
    else blockAndReport += 1;
    if (c.graph_evidence) ringCount += 1;
    if (c.fraud_dna_match) dnaMatchCount += 1;
  }

  return {
    total: cases.length,
    criticalOrHigh: block + blockAndReport,
    review,
    clear,
    ringCount,
    dnaMatchCount,
  };
}

export default async function OverviewPage() {
  const { cases } = await getCases();
  const stats = computeStats(cases);

  // Feature the largest real ring on record — never a synthetic example.
  const ringCases = cases.filter((c) => c.graph_evidence !== null);
  const featured =
    ringCases.length > 0
      ? [...ringCases].sort(
          (a, b) => (b.graph_evidence?.ring_size ?? 0) - (a.graph_evidence?.ring_size ?? 0)
        )[0]
      : null;

  let featuredGraph: CaseGraph | null = null;
  if (featured) {
    try {
      const response = await getCaseGraph(featured.txn_id);
      featuredGraph = response.graph;
    } catch {
      featuredGraph = null;
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <div className="scanline mb-6 flex items-center justify-between rounded-[var(--radius-panel)] border px-5 py-4" style={{ borderColor: "var(--border)", backgroundColor: "var(--graphite)" }}>
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">OVERVIEW</h1>
          <p className="mt-1 text-xs" style={{ color: "var(--graphite-foreground)" }}>
            Live aggregate stats across every case this session has processed.
          </p>
        </div>
        <span className="flex items-center gap-2 text-[11px] font-semibold tracking-wide" style={{ color: "var(--risk-low)" }}>
          <span className="pulse-dot inline-block h-2 w-2 shrink-0 rounded-full bg-current" aria-hidden="true" />
          MONITORING
        </span>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatTile label="Total cases" value={stats.total} />
        <StatTile label="Critical / High" value={stats.criticalOrHigh} accent="var(--risk-high)" />
        <StatTile label="Review" value={stats.review} accent="var(--risk-medium)" />
        <StatTile label="Rings detected" value={stats.ringCount} accent="var(--cobalt)" />
        <StatTile label="Fraud DNA matches" value={stats.dnaMatchCount} accent="var(--risk-critical)" />
      </div>

      <Panel title="Live network — largest active ring on record">
        {featured && featured.graph_evidence ? (
          <>
            <p className="mb-3 text-sm" style={{ color: "var(--foreground)" }}>
              {featured.graph_evidence.evidence_summary}
            </p>
            <FraudRingGraph graph={featuredGraph} />
          </>
        ) : (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No fraud ring has been detected in the current case set.
          </p>
        )}
      </Panel>
    </div>
  );
}

function StatTile({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div
      className="rounded-[var(--radius-panel)] border px-4 py-3 shadow-[var(--shadow-panel)]"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
    >
      <div className="text-[10px] uppercase tracking-wide" style={{ color: "var(--muted)" }}>
        {label}
      </div>
      <div className="mt-1 font-mono text-2xl font-bold" style={{ color: accent ?? "var(--foreground)" }}>
        <AnimatedNumber value={value} />
      </div>
    </div>
  );
}
