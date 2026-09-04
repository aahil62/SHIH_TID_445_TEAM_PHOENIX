"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { submitDecision } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Decision } from "@/lib/types";
import { DECISION_LABEL, DECISION_TONE } from "@/lib/risk";

const OPTIONS: Decision[] = ["clear", "review", "block", "block_and_report"];

export default function DecisionForm({
  txnId,
  currentDecision,
}: {
  txnId: string;
  currentDecision: Decision;
}) {
  const router = useRouter();
  const [selected, setSelected] = useState<Decision>(currentDecision);
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState<"idle" | "error" | "success" | "unauthenticated">("idle");
  const [isPending, startTransition] = useTransition();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("idle");
    const token = getToken();
    if (!token) {
      setStatus("unauthenticated");
      return;
    }
    startTransition(async () => {
      try {
        await submitDecision({ txn_id: txnId, decision: selected, notes: notes || undefined }, token);
        setStatus("success");
        router.refresh();
      } catch {
        setStatus("error");
      }
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {OPTIONS.map((option) => {
          const isSelected = selected === option;
          const tone = DECISION_TONE[option];
          return (
            <button
              key={option}
              type="button"
              onClick={() => setSelected(option)}
              className="rounded-[var(--radius-control)] border px-3 py-1.5 text-sm font-medium transition-colors"
              style={{
                borderColor: isSelected ? tone.fg : "var(--border)",
                backgroundColor: isSelected ? tone.bg : "var(--panel)",
                color: isSelected ? tone.fg : "var(--foreground)",
              }}
            >
              {DECISION_LABEL[option]}
            </button>
          );
        })}
      </div>

      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes for the audit trail (optional)"
        rows={2}
        className="w-full rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
      />

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isPending}
          className="w-fit rounded-[var(--radius-control)] px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-60"
          style={{ backgroundColor: "var(--cobalt)", color: "var(--cobalt-foreground)" }}
        >
          {isPending ? "Submitting…" : "Submit decision"}
        </button>
        {status === "success" && (
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium"
            style={{ color: "var(--risk-low)" }}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            Decision recorded.
          </span>
        )}
        {status === "error" && (
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium"
            style={{ color: "var(--risk-high)" }}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            Couldn&apos;t submit. Try again.
          </span>
        )}
        {status === "unauthenticated" && (
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium"
            style={{ color: "var(--risk-high)" }}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            You&apos;re not signed in — decisions require a logged-in analyst.
          </span>
        )}
      </div>
    </form>
  );
}
