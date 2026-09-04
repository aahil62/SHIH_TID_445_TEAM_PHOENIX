import Link from "next/link";
import { getCaseGraph, getNetworkSummary } from "@/lib/api";
import FraudRingGraph from "@/components/FraudRingGraph";
import type { CaseGraph, NetworkRing } from "@/lib/types";

/** Dedicated, large-workspace investigation view for one fraud ring's
 * network graph — reached from /network's ring panel or /case's Fraud
 * ring panel via "Open Full View". Reuses the exact same graph data and
 * fetching as those two pages (getNetworkSummary + getCaseGraph); this
 * route only decides *which* ring's graph to show and renders it with
 * more room, via FraudRingGraph's existing mode="full". */
export default async function NetworkExplorePage({
  searchParams,
}: PageProps<"/network/explore">) {
  const params = await searchParams;
  const txnIdParam = typeof params.txn_id === "string" ? params.txn_id : undefined;
  const ringParam = typeof params.ring === "string" ? params.ring : undefined;

  let summary;
  try {
    summary = await getNetworkSummary();
  } catch {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-sm font-medium" style={{ color: "var(--risk-high)" }}>
          Couldn&apos;t load the fraud network — the backend may be unreachable.
        </p>
        <Link href="/network" className="text-xs underline-offset-2 hover:underline" style={{ color: "var(--cobalt)" }}>
          ← Back to Fraud Network
        </Link>
      </div>
    );
  }

  let contextRing: NetworkRing | undefined = ringParam
    ? summary.rings.find((r) => r.ring_id === ringParam)
    : undefined;
  let targetTxnId = txnIdParam ?? contextRing?.txn_id;
  if (!targetTxnId) {
    contextRing = summary.rings[0];
    targetTxnId = contextRing?.txn_id;
  }

  let graph: CaseGraph | null = null;
  if (targetTxnId) {
    try {
      graph = (await getCaseGraph(targetTxnId)).graph;
    } catch {
      graph = null;
    }
  }

  // Where "Back" should go: to the case that opened this view (if it
  // came from /case), otherwise to this ring's row on /network, otherwise
  // plain /network — real route context, never a generic dead end.
  const backHref = txnIdParam
    ? (`/case?txn_id=${encodeURIComponent(txnIdParam)}` as const)
    : contextRing
      ? (`/network?ring=${encodeURIComponent(contextRing.ring_id)}#ring-${encodeURIComponent(contextRing.ring_id)}` as const)
      : ("/network" as const);

  return (
    <div className="flex h-full flex-col">
      <div
        className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b px-6 py-3"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
      >
        <Link
          href={backHref}
          className="flex items-center gap-1.5 text-xs font-semibold underline-offset-2 hover:underline"
          style={{ color: "var(--cobalt)" }}
          aria-label="Back to the previous network or case view"
        >
          ← Back
        </Link>
        <div className="h-4 w-px" style={{ backgroundColor: "var(--border)" }} aria-hidden="true" />
        <h1 className="text-sm font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Fraud Network Intelligence
        </h1>
        {contextRing && (
          <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
            Ring {contextRing.ring_id} · {contextRing.ring_size} accounts
            {contextRing.fraud_type ? ` · ${contextRing.fraud_type.replace(/_/g, " ")}` : ""}
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 p-4">
        <FraudRingGraph graph={graph} mode="full" />
      </div>
    </div>
  );
}
