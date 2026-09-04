export default function Panel({
  title,
  children,
  accent,
  raised,
  id,
  highlighted,
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
  /** Anchor id — lets another page link/scroll directly to this panel. */
  id?: string;
  /** Marks this panel as the target of an incoming cross-link (e.g. from
   * /network or /fraud-dna) with an amber ring — amber is reserved for
   * Fraud DNA/network content, so this only ever fires from that link. */
  highlighted?: boolean;
  /** Optional action(s) right-aligned in the header row next to the
   * title — e.g. an "Open Full View" link. Doesn't change the panel's
   * size, just uses the header space that's already there. */
  headerRight?: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="panel-fade-in scroll-mt-6 rounded-[var(--radius-panel)] border px-5 py-4 backdrop-blur-xl transition-[box-shadow,border-color]"
      style={{
        borderColor: highlighted ? "var(--amber)" : "var(--border)",
        backgroundColor: "var(--panel)",
        boxShadow: highlighted
          ? "0 0 0 1px var(--amber), var(--shadow-panel-raised)"
          : raised
            ? "var(--shadow-panel-raised)"
            : "var(--shadow-panel)",
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
