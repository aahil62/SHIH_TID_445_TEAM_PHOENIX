export default function Panel({
  title,
  children,
  accent,
  raised,
}: {
  title: string;
  children: React.ReactNode;
  /** A risk-tone CSS color (e.g. from DECISION_TONE) for the left edge —
   * use only to reflect an actual risk state, never decoratively. */
  accent?: string;
  /** Slightly more visual weight for the single most important panel on
   * a page (e.g. the primary recommendation) — not for general use. */
  raised?: boolean;
}) {
  return (
    <section
      className="rounded-[var(--radius-panel)] border px-5 py-4"
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--panel)",
        boxShadow: raised ? "var(--shadow-panel-raised)" : "var(--shadow-panel)",
        borderLeftWidth: accent ? "3px" : undefined,
        borderLeftColor: accent,
      }}
    >
      <h2
        className="mb-3 text-[11px] font-semibold uppercase tracking-wider"
        style={{ color: "var(--muted)" }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
