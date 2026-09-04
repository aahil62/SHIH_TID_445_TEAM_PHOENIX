export default function Panel({
  title,
  children,
  accent,
  raised,
  headerRight,
}: {
  title: string;
  children: React.ReactNode;
  /** A risk-tone CSS color (e.g. from DECISION_TONE) for the left edge —
   * use only to reflect an actual risk state, never decoratively. */
  accent?: string;
  /** Slightly more visual weight for the single most important panel on
   * a page (e.g. the primary recommendation) — not for general use. */
  raised?: boolean;
  /** Optional action(s) right-aligned in the header row next to the
   * title — e.g. an "Open Full View" link. Doesn't change the panel's
   * size, just uses the header space that's already there. */
  headerRight?: React.ReactNode;
}) {
  return (
    <section
      className="rounded-[var(--radius-panel)] border px-5 py-4 backdrop-blur-xl"
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--panel)",
        boxShadow: raised ? "var(--shadow-panel-raised)" : "var(--shadow-panel)",
        borderLeftWidth: accent ? "3px" : undefined,
        borderLeftColor: accent,
      }}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
          {title}
        </h2>
        {headerRight}
      </div>
      {children}
    </section>
  );
}
