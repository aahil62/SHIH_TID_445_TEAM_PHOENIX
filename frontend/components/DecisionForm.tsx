"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { submitDecision } from "@/lib/api";
import type { Decision } from "@/lib/types";
import { DECISION_LABEL } from "@/lib/risk";

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
  const [status, setStatus] = useState<"idle" | "error" | "success">("idle");
  const [isPending, startTransition] = useTransition();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("idle");
    startTransition(async () => {
      try {
        await submitDecision({ txn_id: txnId, decision: selected, notes: notes || undefined });
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
        {OPTIONS.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setSelected(option)}
            className="rounded border px-3 py-1.5 text-sm font-medium transition-colors"
            style={{
              borderColor: selected === option ? "var(--cobalt)" : "var(--border)",
              backgroundColor: selected === option ? "var(--cobalt)" : "var(--panel)",
              color: selected === option ? "var(--cobalt-foreground)" : "var(--foreground)",
            }}
          >
            {DECISION_LABEL[option]}
          </button>
        ))}
      </div>

      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes for the audit trail (optional)"
        rows={2}
        className="w-full rounded border px-3 py-2 text-sm outline-none"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
      />

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isPending}
          className="w-fit rounded px-4 py-2 text-sm font-medium disabled:opacity-60"
          style={{ backgroundColor: "var(--cobalt)", color: "var(--cobalt-foreground)" }}
        >
          {isPending ? "Submitting..." : "Submit decision"}
        </button>
        {status === "success" && (
          <span className="text-xs" style={{ color: "var(--risk-low)" }}>
            Decision recorded.
          </span>
        )}
        {status === "error" && (
          <span className="text-xs" style={{ color: "var(--risk-high)" }}>
            Couldn&apos;t submit. Try again.
          </span>
        )}
      </div>
    </form>
  );
}
