import Link from "next/link";
import { getCase } from "@/lib/api";
import DecisionBadge from "@/components/DecisionBadge";
import DecisionForm from "@/components/DecisionForm";
import Panel from "@/components/Panel";
import { formatAmount, formatScore, formatTimestamp } from "@/lib/risk";
import { plainReason } from "@/lib/reasons";

export default async function CasePage({
  searchParams,
}: PageProps<"/case">) {
  const params = await searchParams;
  const txnId = typeof params.txn_id === "string" ? params.txn_id : undefined;

  if (!txnId) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-6">
        <p style={{ color: "var(--muted)" }}>
          No transaction selected. Go back to the{" "}
          <Link href="/feed" className="underline" style={{ color: "var(--cobalt)" }}>
            alert feed
          </Link>{" "}
          and pick one.
        </p>
      </div>
    );
  }

  let caseDetail;
  try {
    caseDetail = await getCase(txnId);
  } catch {
    return (
      <div className="mx-auto max-w-3xl px-6 py-6">
        <p style={{ color: "var(--risk-high)" }}>
          Couldn&apos;t load case {txnId}. It may not exist.
        </p>
      </div>
    );
  }

  const { transaction, agent_scores, graph_evidence, fraud_dna_match } = caseDetail;

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <div className="mb-4 flex items-center justify-between">
        <Link href="/feed" className="text-xs underline" style={{ color: "var(--cobalt)" }}>
          ← Back to alert feed
        </Link>
        <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
          {caseDetail.case_id}
        </span>
      </div>

      <div className="flex flex-col gap-4">
        {/* Plain-language summary, leads with recommended action + confidence */}
        <Panel title="Recommendation">
          <div className="flex items-center gap-2">
            <DecisionBadge decision={caseDetail.decision} />
            <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
              {formatScore(caseDetail.confidence)} confidence · risk score {formatScore(caseDetail.final_score)}
            </span>
          </div>
          <p className="mt-3 text-sm" style={{ color: "var(--foreground)" }}>
            {caseDetail.recommended_action}
          </p>

          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
            <div>
              <dt style={{ color: "var(--muted)" }}>Amount</dt>
              <dd className="font-mono">{formatAmount(transaction.amount)}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Merchant</dt>
              <dd className="capitalize">{transaction.merchant_category.replace(/_/g, " ")}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Channel</dt>
              <dd className="capitalize">{transaction.channel.replace(/_/g, " ")}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Account</dt>
              <dd className="font-mono">{transaction.account_id}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Location</dt>
              <dd className="capitalize">{transaction.location}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Time</dt>
              <dd className="font-mono">{formatTimestamp(transaction.timestamp)}</dd>
            </div>
          </dl>
        </Panel>

        {/* Agent evidence */}
        <Panel title="Agent evidence">
          <div className="flex flex-col divide-y" style={{ borderColor: "var(--border)" }}>
            {agent_scores.map((agent) => (
              <div key={agent.agent_name} className="py-2.5 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">
                    {agent.agent_name.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
                    score {formatScore(agent.score)} · confidence {formatScore(agent.confidence)}
                  </span>
                </div>
                {agent.reasons.length > 0 && (
                  <ul className="mt-1 list-inside list-disc text-xs" style={{ color: "var(--muted)" }}>
                    {agent.reasons.map((reason, i) => (
                      <li key={i}>{plainReason(reason)}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </Panel>

        {/* Graph evidence, only when present */}
        {graph_evidence && (
          <Panel title="Graph evidence">
            <p className="mb-3 text-sm" style={{ color: "var(--foreground)" }}>
              {graph_evidence.evidence_summary}
            </p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
              <div>
                <dt style={{ color: "var(--muted)" }}>Ring size</dt>
                <dd className="font-mono">{graph_evidence.ring_size}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Connected accounts</dt>
                <dd className="font-mono">{graph_evidence.connected_accounts}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Shared devices</dt>
                <dd className="font-mono">{graph_evidence.shared_devices}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Shared IPs</dt>
                <dd className="font-mono">{graph_evidence.shared_ips}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Shared merchants</dt>
                <dd className="font-mono">{graph_evidence.shared_merchants}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Graph density</dt>
                <dd className="font-mono">{graph_evidence.graph_density.toFixed(2)}</dd>
              </div>
            </dl>
            {graph_evidence.suspicious_cluster && (
              <p
                className="mt-3 rounded px-2 py-1 text-xs font-medium"
                style={{ color: "var(--risk-high)", backgroundColor: "var(--risk-high-bg)" }}
              >
                Flagged as part of a suspicious cluster · ring {graph_evidence.ring_id}
              </p>
            )}
          </Panel>
        )}

        {/* Fraud DNA match, only when present */}
        {fraud_dna_match && (
          <Panel title="Fraud DNA match">
            <div className="mb-2 flex items-center gap-2">
              <span className="text-sm font-medium capitalize">
                {fraud_dna_match.fraud_type.replace(/_/g, " ")}
              </span>
              <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
                {formatScore(fraud_dna_match.similarity_score)} similarity · ring{" "}
                {fraud_dna_match.matched_ring_id}
              </span>
            </div>
            <p className="text-sm" style={{ color: "var(--foreground)" }}>
              {fraud_dna_match.description}
            </p>
            <p className="mt-2 text-xs" style={{ color: "var(--muted)" }}>
              Modus operandi: {fraud_dna_match.modus_operandi}
            </p>
            <p className="mt-2 text-xs font-medium" style={{ color: "var(--risk-high)" }}>
              {fraud_dna_match.recommendation}
            </p>
          </Panel>
        )}

        {/* Decision submission */}
        <Panel title="Analyst decision">
          <DecisionForm txnId={caseDetail.txn_id} currentDecision={caseDetail.decision} />
        </Panel>
      </div>
    </div>
  );
}
