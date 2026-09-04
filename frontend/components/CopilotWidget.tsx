"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { askCopilot } from "@/lib/api";

type ChatMessage = {
  role: "user" | "assistant" | "system";
  text: string;
};

function CopilotWidgetInner() {
  // Auto-detect the transaction in view (e.g. /case?txn_id=...) so the
  // widget carries context across navigation without the analyst having
  // to repeat the id every time — read from the real URL, not guessed.
  // useSearchParams() re-renders on navigation on its own; no manual
  // effect/state syncing needed.
  const searchParams = useSearchParams();
  const txnId = searchParams.get("txn_id") ?? undefined;

  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending, open]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || pending) return;
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setPending(true);
    try {
      const response = await askCopilot({ question: q, txn_id: txnId });
      setMessages((prev) => [...prev, { role: "assistant", text: response.answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          text: "Copilot is unavailable — the backend needs a GROQ_API_KEY configured to answer questions.",
        },
      ]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2">
      {open && (
        <div
          className="flex h-96 w-80 flex-col overflow-hidden rounded-[var(--radius-panel)] border"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--panel)",
            boxShadow: "var(--shadow-panel-raised)",
          }}
        >
          <div
            className="flex items-center justify-between border-b px-3 py-2"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--graphite)" }}
          >
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ backgroundColor: "var(--risk-low)" }}
                aria-hidden="true"
              />
              <span className="text-xs font-semibold tracking-widest text-white">COPILOT</span>
              {txnId && (
                <span className="font-mono text-[10px]" style={{ color: "var(--graphite-foreground)" }}>
                  {txnId}
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-[var(--radius-control)] px-1.5 py-0.5 text-xs"
              style={{ color: "var(--graphite-foreground)" }}
              aria-label="Close Copilot"
            >
              ✕
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2">
            {messages.length === 0 && (
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Ask about a transaction — e.g. &quot;why was this flagged?&quot; or &quot;is this
                account connected to a ring?&quot;
                {!txnId && " Open a case first, or give a transaction id in your question."}
              </p>
            )}
            <div className="flex flex-col gap-2">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className="max-w-[85%] rounded-[var(--radius-control)] px-2.5 py-1.5 text-xs leading-relaxed"
                  style={{
                    alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                    backgroundColor:
                      m.role === "user"
                        ? "var(--cobalt)"
                        : m.role === "system"
                          ? "var(--risk-medium-bg)"
                          : "var(--canvas)",
                    color:
                      m.role === "user"
                        ? "var(--cobalt-foreground)"
                        : m.role === "system"
                          ? "var(--risk-medium)"
                          : "var(--foreground)",
                  }}
                >
                  {m.text}
                </div>
              ))}
              {pending && (
                <div
                  className="max-w-[85%] self-start rounded-[var(--radius-control)] px-2.5 py-1.5 text-xs"
                  style={{ backgroundColor: "var(--canvas)", color: "var(--muted)" }}
                >
                  Thinking…
                </div>
              )}
            </div>
          </div>

          <form onSubmit={handleSend} className="flex items-center gap-2 border-t p-2" style={{ borderColor: "var(--border)" }}>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask Copilot…"
              className="min-w-0 flex-1 rounded-[var(--radius-control)] border px-2 py-1.5 text-xs outline-none"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--canvas)", color: "var(--foreground)" }}
            />
            <button
              type="submit"
              disabled={pending || !question.trim()}
              className="shrink-0 rounded-[var(--radius-control)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
              style={{ backgroundColor: "var(--cobalt)", color: "var(--cobalt-foreground)" }}
            >
              Send
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-12 w-12 items-center justify-center rounded-full transition-transform hover:scale-105"
        style={{
          backgroundColor: "var(--cobalt)",
          color: "var(--cobalt-foreground)",
          boxShadow: "var(--shadow-panel-raised)",
        }}
        aria-label={open ? "Close Copilot" : "Open Copilot"}
        aria-expanded={open}
      >
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" aria-hidden="true">
          <path d="M4 5h16v10H8l-4 4V5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
          <circle cx="9" cy="10" r="1" fill="currentColor" />
          <circle cx="12" cy="10" r="1" fill="currentColor" />
          <circle cx="15" cy="10" r="1" fill="currentColor" />
        </svg>
      </button>
    </div>
  );
}

/** Floating chat, present on every route (mounted once in layout.tsx).
 * Every answer comes from the real POST /copilot/chat — grounded in
 * CaseEngine data by construction on the backend (see
 * fraudlens/core/copilot/agent.py). This widget never phrases or
 * augments an answer itself; it only renders response.answer verbatim,
 * and shows an explicit unavailable state on failure (e.g. no
 * GROQ_API_KEY configured server-side) rather than inventing a reply.
 * Wrapped in Suspense because useSearchParams() requires it. */
export default function CopilotWidget() {
  return (
    <Suspense fallback={null}>
      <CopilotWidgetInner />
    </Suspense>
  );
}
