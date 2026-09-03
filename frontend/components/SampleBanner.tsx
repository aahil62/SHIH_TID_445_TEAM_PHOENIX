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
      <svg viewBox="0 0 16 16" fill="none" className="h-3.5 w-3.5 shrink-0" aria-hidden="true">
        <path
          d="M8 1.5 15 14H1L8 1.5Z"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinejoin="round"
        />
        <path d="M8 6.5v3.2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        <circle cx="8" cy="11.6" r="0.9" fill="currentColor" />
      </svg>
      Sample workspace — synthetic data, not a production system
    </div>
  );
}
