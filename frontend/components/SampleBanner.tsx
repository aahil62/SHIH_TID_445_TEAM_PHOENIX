export default function SampleBanner() {
  return (
    <div
      className="flex items-center gap-2 border-b px-4 py-1.5 text-xs font-medium"
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--risk-medium-bg)",
        color: "var(--risk-medium)",
      }}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
      Sample workspace — synthetic data, not a production system
    </div>
  );
}
