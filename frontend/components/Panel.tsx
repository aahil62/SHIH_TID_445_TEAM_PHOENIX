export default function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-lg border px-5 py-4"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
    >
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--muted)" }}>
        {title}
      </h2>
      {children}
    </section>
  );
}
