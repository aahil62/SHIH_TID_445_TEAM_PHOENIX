import Link from "next/link";
import { getCase, getCaseGraph } from "@/lib/api";
import CopilotChat from "@/components/CopilotChat";
import DecisionForm from "@/components/DecisionForm";
import FraudRingGraph from "@/components/FraudRingGraph";
import MaskedId from "@/components/MaskedId";
import Panel from "@/components/Panel";
import SignalBar from "@/components/SignalBar";
import { formatAmount, formatScore, formatTimestamp, DECISION_TONE } from "@/lib/risk";
import { RISK_TIER_LABEL } from "@/lib/tier";
import { formatAgentName } from "@/lib/agents";
import { plainReason } from "@/lib/reasons";
import type { CaseGraph } from "@/lib/types";

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

  // A failed graph fetch is treated exactly like "no ring" (null) — never
  // fabricated, never silently different from the documented empty state.
  let caseGraph: CaseGraph | null = null;
  try {
    const graphResponse = await getCaseGraph(txnId);
    caseGraph = graphResponse.graph;
  } catch {
    caseGraph = null;
  }

  const { transaction, agent_scores, fraud_dna_match, graph_evidence } = caseDetail;
  const tone = DECISION_TONE[caseDetail.decision];
  const sortedSignals = [...agent_scores].sort((a, b) => b.score - a.score);

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <div className="mb-4 flex items-center justify-between">
        <Link
          href="/feed"
          className="rounded-sm text-xs font-medium underline underline-offset-2"
          style={{ color: "var(--cobalt)" }}
        >
          ← Back to feed
        </Link>
        <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
          {caseDetail.case_id}
        </span>
      </div>

      <h1 className="mb-4 text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
        Case Investigation
      </h1>

      <div className="flex flex-col gap-4">
        {/* 1. CASE SUMMARY */}
        <Panel title="Case summary" accent={tone.fg} raised>
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-bold tracking-wide" style={{ color: tone.fg }}>
              {RISK_TIER_LABEL[caseDetail.decision]}
            </span>
            {caseDetail.system_action === "auto_held" && (
              <span
                className="rounded-[var(--radius-control)] px-2 py-0.5 text-[11px] font-bold tracking-wide"
                style={{ backgroundColor: "var(--risk-medium-bg)", color: "var(--risk-medium)" }}
                title="Held automatically pending review — no real transaction was stopped. Clears the instant an analyst records a decision."
              >
                AUTO-HELD
              </span>
            )}
            {caseDetail.is_false_positive && (
              <span
                className="rounded-[var(--radius-control)] px-2 py-0.5 text-[11px] font-bold tracking-wide"
                style={{ backgroundColor: "var(--cobalt)", color: "var(--cobalt-foreground)" }}
                title="This case was flagged by the engine, investigated, and confirmed to NOT represent actual fraud — distinct from a transaction that was simply never risky."
              >
                FALSE POSITIVE
              </span>
            )}
            {caseDetail.account_restricted && (
              <span
                className="rounded-[var(--radius-control)] px-2 py-0.5 text-[11px] font-bold tracking-wide"
                style={{ backgroundColor: "rgba(216,138,69,0.14)", color: "var(--amber)" }}
                title="This account's velocity thresholds are tightened, auto-applied after a prior high-confidence hold. Clears the instant an analyst records a decision on the triggering case."
              >
                ACCOUNT RESTRICTED
              </span>
            )}
            <span className="font-mono text-sm font-semibold">
              {formatAmount(transaction.amount)} transaction
            </span>
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              Account <MaskedId value={transaction.account_id} />
            </span>
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs" style={{ color: "var(--muted)" }}>
            <span>
              {formatScore(caseDetail.confidence)} confidence · risk score{" "}
              {formatScore(caseDetail.final_score)}
            </span>
            <span className="capitalize">
              {transaction.merchant_category.replace(/_/g, " ")} ·{" "}
              {transaction.channel.replace(/_/g, " ")}
            </span>
            <span className="font-mono">{formatTimestamp(transaction.timestamp)}</span>
          </div>
          <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--foreground)" }}>
            {caseDetail.recommended_action}
          </p>
        </Panel>

        {/* 2. WHY THIS WAS FLAGGED */}
        <Panel title="Why this was flagged">
          {caseDetail.explanation_reasons.length > 0 ? (
            <ul className="flex flex-col gap-1.5 text-sm" style={{ color: "var(--foreground)" }}>
              {caseDetail.explanation_reasons.map((reason, i) => (
                <li key={i}>{plainReason(reason)}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No specific risk factors were flagged for this transaction.
            </p>
          )}
        </Panel>

        {/* 3. RISK SIGNALS — every real agent_scores entry, not a fixed taxonomy */}
        <Panel title="Risk signals">
          {sortedSignals.length > 0 ? (
            <div className="flex flex-col gap-3">
              {sortedSignals.map((signal, i) => (
                <div key={signal.agent_name} className="flex items-start gap-2">
                  <span
                    className="mt-0.5 shrink-0 font-mono text-xs"
                    style={{ color: "var(--border)" }}
                    aria-hidden="true"
                  >
                    {i === sortedSignals.length - 1 ? "└──" : "├──"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <SignalBar label={formatAgentName(signal.agent_name)} score={signal.score} />
                    {signal.reasons.length > 0 && (
                      <ul className="mt-1 flex flex-col gap-0.5 pl-1 text-[11px]" style={{ color: "var(--muted)" }}>
                        {signal.reasons.map((reason, j) => (
                          <li key={j}>{plainReason(reason)}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No signal data available for this case.
            </p>
          )}
        </Panel>

        {/* 4. FRAUD RING — real interactive graph, or an explicit empty state */}
        <Panel title="Fraud ring">
          {graph_evidence && (
            <p className="mb-3 text-sm leading-relaxed" style={{ color: "var(--foreground)" }}>
              {graph_evidence.evidence_summary}
            </p>
          )}
          <FraudRingGraph graph={caseGraph} />
        </Panel>

        {/* 5. FRAUD DNA — only real content when present, explicit empty state when not */}
        <Panel title="Fraud DNA">
          {fraud_dna_match ? (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="text-sm font-medium capitalize">
                  {fraud_dna_match.fraud_type.replace(/_/g, " ")}
                </span>
                <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
                  {formatScore(fraud_dna_match.similarity_score)} similarity · ring{" "}
                  {fraud_dna_match.matched_ring_id}
                </span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: "var(--foreground)" }}>
                {fraud_dna_match.description}
              </p>
              <p className="mt-2 text-xs" style={{ color: "var(--muted)" }}>
                Modus operandi: {fraud_dna_match.modus_operandi}
              </p>
              <p className="mt-2 text-xs font-medium" style={{ color: "var(--risk-high)" }}>
                {fraud_dna_match.recommendation}
              </p>
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No Fraud DNA match — this case has not been matched to a known fraud pattern.
            </p>
          )}
        </Panel>

        {/* 6. ASK COPILOT — pre-filled with this transaction's ID so a
            question like "why was this flagged?" needs no typing beyond
            the question itself. */}
        <Panel title="Ask Copilot">
          <CopilotChat txnId={caseDetail.txn_id} />
        </Panel>

        {/* 7. DECISION */}
        <Panel title="Decision">
          <DecisionForm txnId={caseDetail.txn_id} currentDecision={caseDetail.decision} />
        </Panel>
      </div>
    </div>
  );
}
