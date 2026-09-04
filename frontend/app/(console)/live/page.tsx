"use client";

import { useEffect, useRef, useState } from "react";
import Panel from "@/components/Panel";
import { formatAmount, formatScore } from "@/lib/risk";
import { formatAgentName } from "@/lib/agents";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";

const AGENT_ORDER = [
  "rule_agent", "velocity_agent", "behavioral_agent", "graph_agent", "ml_agent", "fraud_dna_agent",
];

interface AgentReveal {
  score: number;
  confidence: number;
  reason: string;
}

interface InFlight {
  txn_id: string;
  account_id: string;
  amount: number;
  merchant_category: string;
  channel: string;
  agents: Partial<Record<string, AgentReveal>>;
  decision: { final_score: number; confidence: number; decision: string } | null;
  autonomous: boolean;
}

interface CompletedRow {
  txn_id: string;
  amount: number;
  merchant_category: string;
  final_score: number;
  decision: string;
  autonomous: boolean;
}

const DECISION_COLOR: Record<string, string> = {
  clear: "var(--risk-low)",
  review: "var(--risk-medium)",
  block: "var(--risk-high)",
  block_and_report: "var(--risk-critical)",
};

export default function LiveFeedPage() {
  const [connected, setConnected] = useState(false);
  const [current, setCurrent] = useState<InFlight | null>(null);
  const [history, setHistory] = useState<CompletedRow[]>([]);
  const sourceRef = useRef<EventSource | null>(null);
  // "ingested" always arrives before "decision" for the same txn_id, so
  // the decision handler can read this synchronously to build a complete
  // history row immediately — no need to backfill state after the fact.
  const metaByTxnId = useRef<Map<string, { amount: number; merchant_category: string }>>(new Map());

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/live/stream?interval_seconds=2.5`);
    sourceRef.current = source;

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);

    source.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "ingested") {
        metaByTxnId.current.set(data.txn_id, {
          amount: data.amount,
          merchant_category: data.merchant_category,
        });
        setCurrent({
          txn_id: data.txn_id,
          account_id: data.account_id,
          amount: data.amount,
          merchant_category: data.merchant_category,
          channel: data.channel,
          agents: {},
          decision: null,
          autonomous: false,
        });
        return;
      }

      if (data.type === "agent_scored") {
        setCurrent((prev) =>
          prev && prev.txn_id === data.txn_id
            ? {
                ...prev,
                agents: {
                  ...prev.agents,
                  [data.agent_name]: {
                    score: data.score,
                    confidence: data.confidence,
                    reason: data.reason,
                  },
                },
              }
            : prev
        );
        return;
      }

      if (data.type === "decision") {
        setCurrent((prev) =>
          prev && prev.txn_id === data.txn_id
            ? {
                ...prev,
                decision: {
                  final_score: data.final_score,
                  confidence: data.confidence,
                  decision: data.decision,
                },
              }
            : prev
        );
        const meta = metaByTxnId.current.get(data.txn_id);
        setHistory((prev) => [
          {
            txn_id: data.txn_id,
            amount: meta?.amount ?? 0,
            merchant_category: meta?.merchant_category ?? "",
            final_score: data.final_score,
            decision: data.decision,
            autonomous: false,
          },
          ...prev,
        ].slice(0, 12));
        return;
      }

      if (data.type === "autonomous_action") {
        setCurrent((prev) => (prev && prev.txn_id === data.txn_id ? { ...prev, autonomous: true } : prev));
        setHistory((prev) =>
          prev.map((r) => (r.txn_id === data.txn_id ? { ...r, autonomous: true } : r))
        );
      }
    };

    return () => {
      source.close();
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
            Live Transaction Feed
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
            Real ingestion, real scoring, real decisions — computed live as each transaction streams in,
            not pre-loaded.
          </p>
        </div>
        <span
          className="flex items-center gap-1.5 text-xs font-semibold"
          style={{ color: connected ? "var(--risk-low)" : "var(--muted)" }}
        >
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full bg-current ${connected ? "animate-pulse" : ""}`}
          />
          {connected ? "STREAMING" : "CONNECTING…"}
        </span>
      </div>

      <Panel title="Pipeline — current transaction" raised>
        {!current ? (
          <p className="py-8 text-center text-sm" style={{ color: "var(--muted)" }}>
            Waiting for the first transaction…
          </p>
        ) : (
          <div>
            <div className="mb-5 flex flex-wrap items-center gap-4">
              <span className="font-mono text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                {current.txn_id}
              </span>
              <span className="font-mono text-sm" style={{ color: "var(--muted)" }}>
                {formatAmount(current.amount)}
              </span>
              <span className="text-xs capitalize" style={{ color: "var(--muted)" }}>
                {current.merchant_category.replace(/_/g, " ")} · {current.channel.replace(/_/g, " ")}
              </span>
              <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
                {current.account_id}
              </span>
            </div>

            <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {AGENT_ORDER.map((name) => {
                const reveal = current.agents[name];
                const lit = Boolean(reveal);
                return (
                  <div
                    key={name}
                    className="rounded-[var(--radius-control)] border px-3 py-2.5 transition-all duration-300"
                    style={{
                      borderColor: lit ? "var(--cobalt)" : "var(--border)",
                      backgroundColor: lit ? "rgba(22,163,106,0.08)" : "transparent",
                      opacity: lit ? 1 : 0.4,
                    }}
                  >
                    <div className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--muted)" }}>
                      {formatAgentName(name)}
                    </div>
                    <div className="mt-1 font-mono text-sm font-semibold" style={{ color: lit ? "var(--cobalt)" : "var(--muted)" }}>
                      {reveal ? formatScore(reveal.score) : "—"}
                    </div>
                  </div>
                );
              })}
            </div>

            {current.decision && (
              <div
                className="flex flex-wrap items-center gap-3 rounded-[var(--radius-control)] border px-4 py-3"
                style={{
                  borderColor: DECISION_COLOR[current.decision.decision],
                  backgroundColor: `${DECISION_COLOR[current.decision.decision]}1a`,
                }}
              >
                <span
                  className="text-sm font-bold uppercase tracking-wide"
                  style={{ color: DECISION_COLOR[current.decision.decision] }}
                >
                  {current.decision.decision.replace(/_/g, " ")}
                </span>
                <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
                  risk {formatScore(current.decision.final_score)} · confidence{" "}
                  {formatScore(current.decision.confidence)}
                </span>
                {current.autonomous && (
                  <span
                    className="rounded-[var(--radius-control)] px-2 py-0.5 text-[10px] font-bold tracking-wide"
                    style={{ backgroundColor: "var(--risk-medium-bg)", color: "var(--risk-medium)" }}
                  >
                    AUTONOMOUS ACTION TAKEN
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </Panel>

      <div className="mt-4">
        <Panel title="Recently processed">
          {history.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Nothing processed yet.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {history.map((row, i) => (
                <div
                  key={`${row.txn_id}-${i}`}
                  className="flex items-center gap-3 rounded-[var(--radius-control)] px-2 py-1.5 text-sm"
                >
                  <span className="w-40 shrink-0 truncate font-mono text-xs" style={{ color: "var(--muted)" }}>
                    {row.txn_id}
                  </span>
                  <span className="font-mono text-xs" style={{ color: "var(--foreground)" }}>
                    {formatAmount(row.amount)}
                  </span>
                  <span className="flex-1 truncate text-xs capitalize" style={{ color: "var(--muted)" }}>
                    {row.merchant_category.replace(/_/g, " ")}
                  </span>
                  {row.autonomous && (
                    <span className="text-[10px] font-bold" style={{ color: "var(--risk-medium)" }}>
                      AUTO
                    </span>
                  )}
                  <span
                    className="shrink-0 font-mono text-xs font-bold uppercase"
                    style={{ color: DECISION_COLOR[row.decision] }}
                  >
                    {row.decision.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
