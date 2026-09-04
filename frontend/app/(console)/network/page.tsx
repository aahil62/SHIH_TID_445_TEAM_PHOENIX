import Link from "next/link";
import { getCaseGraph, getNetworkSummary } from "@/lib/api";
import FraudRingGraph, { OpenFullViewLink } from "@/components/FraudRingGraph";
import Panel from "@/components/Panel";
import StatCard from "@/components/StatCard";
import { formatScore } from "@/lib/risk";
import type { CaseGraph } from "@/lib/types";

export default async function NetworkPage({
  searchParams,
}: PageProps<"/network">) {
  const params = await searchParams;
  const ringParam = typeof params.ring === "string" ? params.ring : undefined;
  const fraudTypeParam = typeof params.fraud_type === "string" ? params.fraud_type : undefined;

  const summary = await getNetworkSummary();
  // Arriving from /fraud-dna or /case with a specific ring/fraud_type in
  // the URL puts that ring in the main graph panel instead of always
  // defaulting to the largest one — this is what makes the cross-link
  // actually land somewhere relevant instead of just landing on /network.
  const selectedRing =
    (ringParam && summary.rings.find((r) => r.ring_id === ringParam)) ||
    (fraudTypeParam && summary.rings.find((r) => r.fraud_type === fraudTypeParam)) ||
    summary.rings[0];

  let graph: CaseGraph | null = null;
  if (selectedRing) {
    try {
      graph = (await getCaseGraph(selectedRing.txn_id)).graph;
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
          href="/fraud-dna"
        />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Panel
          title={selectedRing ? `Ring ${selectedRing.ring_id}` : "No ring in view"}
          headerRight={
            selectedRing ? (
              <OpenFullViewLink href={`/network/explore?ring=${encodeURIComponent(selectedRing.ring_id)}`} />
            ) : undefined
          }
        >
          {selectedRing ? (
            <>
              <FraudRingGraph graph={graph} mode="compact" />
              {selectedRing.fraud_type && (
                <p className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
                  Matched Fraud DNA pattern:{" "}
                  <Link
                    href={`/fraud-dna?fraud_type=${encodeURIComponent(selectedRing.fraud_type)}`}
                    className="font-semibold underline-offset-2 hover:underline"
                    style={{ color: "var(--amber)" }}
                  >
                    {selectedRing.fraud_type.replace(/_/g, " ")} →
                  </Link>
                </p>
              )}
            </>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No fraud rings detected in the current dataset.
            </p>
          )}
        </Panel>

        <Panel title="All detected rings">
          <div className="flex flex-col gap-2">
            {summary.rings.map((r) => {
              const isSelected = selectedRing?.ring_id === r.ring_id;
              return (
                <div
                  key={r.ring_id}
                  id={`ring-${r.ring_id}`}
                  className="hoverable-panel flex scroll-mt-6 items-center justify-between rounded-[var(--radius-control)] border px-3 py-2 text-xs transition-colors"
                  style={{
                    borderColor: isSelected ? "var(--amber)" : "var(--border)",
                    boxShadow: isSelected ? "0 0 0 1px var(--amber)" : undefined,
                  }}
                >
                  <Link
                    href={`/case?txn_id=${encodeURIComponent(r.txn_id)}`}
                    className="font-mono hover:underline"
                    style={{ color: "var(--foreground)" }}
                  >
                    {r.ring_id}
                  </Link>
                  <span style={{ color: "var(--muted)" }}>{r.ring_size} accounts</span>
                  {r.fraud_type ? (
                    <Link
                      href={`/fraud-dna?fraud_type=${encodeURIComponent(r.fraud_type)}`}
                      className="font-medium underline-offset-2 hover:underline"
                      style={{ color: "var(--amber)" }}
                    >
                      {r.fraud_type.replace(/_/g, " ")}
                    </Link>
                  ) : (
                    <span style={{ color: "var(--muted)" }}>unmatched</span>
                  )}
                </div>
              );
            })}
            {summary.rings.length === 0 && (
              <p className="text-sm" style={{ color: "var(--muted)" }}>No rings to show.</p>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
