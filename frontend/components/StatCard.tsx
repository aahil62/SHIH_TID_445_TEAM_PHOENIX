import Link from "next/link";

export default function StatCard({
  label,
  value,
  color,
  href,
}: {
  label: string;
  value: string | number;
  /** A semantic tone color for the value — omit for the default foreground. */
  color?: string;
  /** When set, the whole card becomes a link to where an analyst would
   * act on this number (e.g. "Pending Reviews" → the alert feed) — makes
   * the stat a call to action, not just a readout. */
  href?: string;
}) {
  const body = (
    <>
      <div
        className="mb-2 text-[11px] font-semibold uppercase tracking-wider"
        style={{ color: "var(--muted)" }}
      >
        {label}
      </div>
      <div className="font-mono text-[28px] font-semibold" style={{ color: color ?? "var(--foreground)" }}>
        {value}
      </div>
    </>
  );

  const className =
    "panel-fade-in block rounded-[var(--radius-panel)] border px-5 py-4 backdrop-blur-xl transition-[border-color,transform]" +
    (href ? " hoverable-panel hover:-translate-y-0.5" : "");
  const style = {
    borderColor: "var(--border)",
    backgroundColor: "var(--panel)",
    boxShadow: "var(--shadow-panel)",
  };

  if (href) {
    return (
      <Link href={href} className={className} style={style}>
        {body}
      </Link>
    );
  }

  return (
    <div className={className} style={style}>
      {body}
    </div>
  );
}
