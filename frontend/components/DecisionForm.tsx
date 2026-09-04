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
  compact = false,
}: {
  txnId: string;
  currentDecision: Decision;
  /** Condensed single-row layout for the sticky decision bar — notes
   * collapse behind a toggle instead of always showing a textarea, so
   * the bar stays a fixed, predictable height while it's pinned on
   * screen. */
  compact?: boolean;
}) {
  const router = useRouter();
  const [selected, setSelected] = useState<Decision>(currentDecision);
  const [notes, setNotes] = useState("");
  const [notesOpen, setNotesOpen] = useState(!compact);
  const [isFalsePositive, setIsFalsePositive] = useState(false);
  const [status, setStatus] = useState<"idle" | "error" | "success" | "unauthenticated">("idle");
  const [isPending, startTransition] = useTransition();

  // Only a case the engine actually flagged can be "corrected" to a false
  // positive — marking one on a transaction that was never risky isn't a
  // correction of anything. Gated on the engine's own recommendation
  // (currentDecision), same source of truth the backend validates against.
  const wasFlagged = currentDecision !== "clear";

  function handleSelectDecision(option: Decision) {
    setSelected(option);
    if (option !== "clear") setIsFalsePositive(false);
  }

  function handleFalsePositiveToggle(checked: boolean) {
    setIsFalsePositive(checked);
    if (checked) setSelected("clear");
  }

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
        await submitDecision(
          {
            txn_id: txnId,
            decision: selected,
            notes: notes || undefined,
            is_false_positive: isFalsePositive || undefined,
          },
          token,
        );
        setStatus("success");
        router.refresh();
      } catch {
        setStatus("error");
      }
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={compact ? "flex flex-wrap items-center gap-2.5" : "flex flex-col gap-3"}
    >
      <div className="flex flex-wrap gap-2">
        {OPTIONS.map((option) => {
          const isSelected = selected === option;
          const tone = DECISION_TONE[option];
          return (
            <button
              key={option}
              type="button"
              onClick={() => handleSelectDecision(option)}
              className={`cursor-pointer rounded-[var(--radius-control)] border font-medium transition-[filter,background-color,border-color] hover:brightness-110 ${
                compact ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm"
              }`}
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

      {wasFlagged && (
        <label className="flex items-start gap-2 text-sm" style={{ color: "var(--foreground)" }}>
          <input
            type="checkbox"
            checked={isFalsePositive}
            onChange={(e) => handleFalsePositiveToggle(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            This was a false positive — investigation confirmed no actual fraud
            {!compact && (
              <span className="block text-xs" style={{ color: "var(--muted)" }}>
                Distinct from an ordinary Clear: records that this case was flagged and
                investigated, not just cleared.
              </span>
            )}
          </span>
        </label>
      )}

      {compact && !notesOpen && (
        <button
          type="button"
          onClick={() => setNotesOpen(true)}
          className="cursor-pointer text-xs underline-offset-2 hover:underline"
          style={{ color: "var(--muted)" }}
        >
          + Add note
        </button>
      )}

      {notesOpen && (
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Notes for the audit trail (optional)"
          rows={compact ? 1 : 2}
          autoFocus={compact}
          className={
            "rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none " +
            (compact ? "w-56" : "w-full")
          }
          style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
        />
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isPending}
          className={
            "w-fit cursor-pointer rounded-[var(--radius-control)] font-medium transition-[filter,opacity] hover:brightness-110 disabled:cursor-default disabled:opacity-60 " +
            (compact ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm")
          }
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
            {isFalsePositive ? "Marked as a false positive." : "Decision recorded."}
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
