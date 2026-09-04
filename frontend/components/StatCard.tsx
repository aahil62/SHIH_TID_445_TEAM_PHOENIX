export default function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  /** A semantic tone color for the value — omit for the default foreground. */
  color?: string;
}) {
  return (
    <div
      className="glass hover-lift rounded-[var(--radius-panel)] border px-5 py-4"
      style={{
        borderColor: color ? `color-mix(in srgb, ${color} 30%, var(--border))` : "var(--border)",
        background: color
          ? `linear-gradient(180deg, color-mix(in srgb, ${color} 7%, transparent), transparent 60%), var(--panel)`
          : "var(--panel)",
        boxShadow: "var(--shadow-panel)",
      }}
    >
      <div
        className="mb-2 text-[11px] font-semibold uppercase tracking-wider"
        style={{ color: "var(--muted)" }}
      >
        {label}
      </div>
      <div className="font-mono text-[28px] font-semibold" style={{ color: color ?? "var(--foreground)" }}>
        {value}
      </div>
    </div>
  );
}
