"use client";

import { useState } from "react";
import { CopilotApiError, sendCopilotMessage } from "@/lib/api";
import type { CopilotToolCall } from "@/lib/types";

interface ChatMessage {
  role: "user" | "assistant" | "error";
  content: string;
  toolCalls?: CopilotToolCall[];
}

const SUGGESTIONS = ["Why was this flagged?", "Why wasn't this flagged?", "Are there any connected accounts?"];

const ROLE_LABEL: Record<ChatMessage["role"], string> = {
  user: "You",
  assistant: "Copilot",
  error: "Error",
};

export default function CopilotChat({ txnId }: { txnId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(question: string) {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendCopilotMessage({ question: trimmed, txn_id: txnId });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, toolCalls: response.tool_calls },
      ]);
    } catch (err) {
      const message =
        err instanceof CopilotApiError
          ? err.status === 503
            ? `Copilot isn't set up yet — ${err.message}`
            : `Copilot couldn't answer — ${err.message}`
          : "Couldn't reach Copilot. Try again.";
      setMessages((prev) => [...prev, { role: "error", content: message }]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <div className="flex flex-col gap-3">
      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => void send(s)}
              disabled={loading}
              className="rounded-[var(--radius-control)] border px-2.5 py-1 text-xs transition-opacity disabled:opacity-60"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex max-h-96 flex-col gap-3 overflow-y-auto pr-1">
          {messages.map((m, i) => (
            <div key={i} className="flex flex-col gap-1">
              <span
                className="text-[11px] font-semibold uppercase tracking-wide"
                style={{
                  color:
                    m.role === "error"
                      ? "var(--risk-high)"
                      : m.role === "assistant"
                        ? "var(--cobalt)"
                        : "var(--muted)",
                }}
              >
                {ROLE_LABEL[m.role]}
              </span>
              <p
                className="text-sm leading-relaxed"
                style={{ color: m.role === "error" ? "var(--risk-high)" : "var(--foreground)" }}
              >
                {m.content}
              </p>
              {m.toolCalls && m.toolCalls.length > 0 && (
                <span className="font-mono text-[11px]" style={{ color: "var(--muted)" }}>
                  Copilot checked: {m.toolCalls.map((t) => t.tool).join(", ")}
                </span>
              )}
            </div>
          ))}
          {loading && (
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              Copilot is thinking…
            </span>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask about ${txnId}…`}
          disabled={loading}
          className="flex-1 rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none disabled:opacity-60"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="w-fit rounded-[var(--radius-control)] px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-60"
          style={{ backgroundColor: "var(--cobalt)", color: "var(--cobalt-foreground)" }}
        >
          {loading ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}
