import Link from "next/link";
import { getCaseGraph, getNetworkSummary } from "@/lib/api";
import FraudRingGraph from "@/components/FraudRingGraph";
import Panel from "@/components/Panel";
import StatCard from "@/components/StatCard";
import { formatScore } from "@/lib/risk";
import type { CaseGraph } from "@/lib/types";

export default async function NetworkPage() {
  const summary = await getNetworkSummary();
  const topRing = summary.rings[0];

  let graph: CaseGraph | null = null;
  if (topRing) {
    try {
      graph = (await getCaseGraph(topRing.txn_id)).graph;
    } catch {
      graph = null;
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Fraud Network
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
          Relationships between accounts, devices, IPs and merchants across every detected ring.
        </p>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Fraud rings" value={summary.ring_count} color="var(--amber)" />
        <StatCard label="Linked accounts" value={summary.linked_accounts} color="var(--amber)" />
        <StatCard label="Shared devices" value={summary.shared_devices} color="var(--amber)" />
        <StatCard
          label="Top Fraud DNA match"
          value={summary.top_dna_match_pct ? formatScore(summary.top_dna_match_pct) : "—"}
          color="var(--amber)"
        />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Panel title={topRing ? `Ring ${topRing.ring_id}` : "No ring in view"}>
          {topRing ? (
            <FraudRingGraph graph={graph} />
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No fraud rings detected in the current dataset.
            </p>
          )}
        </Panel>

        <Panel title="All detected rings">
          <div className="flex flex-col gap-2">
            {summary.rings.map((r) => (
              <Link
                key={r.ring_id}
                href={`/case?txn_id=${encodeURIComponent(r.txn_id)}`}
                className="flex items-center justify-between rounded-[var(--radius-control)] border px-3 py-2 text-xs transition-colors"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="font-mono" style={{ color: "var(--foreground)" }}>{r.ring_id}</span>
                <span style={{ color: "var(--muted)" }}>{r.ring_size} accounts</span>
                <span style={{ color: "var(--amber)" }}>
                  {r.fraud_type ? r.fraud_type.replace(/_/g, " ") : "unmatched"}
                </span>
              </Link>
            ))}
            {summary.rings.length === 0 && (
              <p className="text-sm" style={{ color: "var(--muted)" }}>No rings to show.</p>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
