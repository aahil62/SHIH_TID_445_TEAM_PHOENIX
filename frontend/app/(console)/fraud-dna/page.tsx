import { getDnaPatterns } from "@/lib/api";
import Panel from "@/components/Panel";
import StatCard from "@/components/StatCard";
import { formatScore } from "@/lib/risk";

export default async function FraudDnaPage() {
  const { patterns } = await getDnaPatterns();
  const totalMatches = patterns.reduce((sum, p) => sum + p.matches, 0);
  const topConfidence = Math.max(0, ...patterns.map((p) => p.avg_confidence ?? 0));
  const matchedRings = patterns.filter((p) => p.matches > 0);

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Fraud DNA
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
          Known fraud typologies, fingerprint matches, and library growth.
        </p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Known patterns" value={patterns.length} />
        <StatCard
          label="Top match confidence"
          value={topConfidence > 0 ? formatScore(topConfidence) : "—"}
          color="var(--amber)"
        />
        <StatCard label="Linked rings" value={matchedRings.length} />
        <StatCard label="Total matches" value={totalMatches} color="var(--risk-low)" />
      </div>

      <div className="mb-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
        Pattern Library
      </div>
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {patterns.map((p) => (
          <div
            key={p.ring_id}
            className="hover-lift rounded-[var(--radius-panel)] border px-5 py-4 glass"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)", boxShadow: "var(--shadow-panel)" }}
          >
            <h4 className="mb-1.5 text-sm font-semibold" style={{ color: "var(--foreground)" }}>
              {p.name}
            </h4>
            <p className="mb-3 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {p.description}
            </p>
            <div className="flex items-center justify-between font-mono text-[11px]">
              <span style={{ color: "var(--muted)" }}>{p.matches} matches</span>
              <span style={{ color: "var(--amber)" }} className="font-semibold">
                {p.avg_confidence !== null ? `${formatScore(p.avg_confidence)} conf.` : "no matches yet"}
              </span>
            </div>
          </div>
        ))}
      </div>

      <Panel title="Recent Matches">
        {matchedRings.length > 0 ? (
          <div className="flex flex-col divide-y" style={{ borderColor: "var(--border)" }}>
            {matchedRings.map((p) => (
              <div
                key={p.ring_id}
                className="flex items-center gap-4 py-2.5 text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="w-40 shrink-0 font-mono text-xs" style={{ color: "var(--muted)" }}>
                  {p.ring_id}
                </span>
                <span className="flex-1" style={{ color: "var(--foreground)" }}>{p.name}</span>
                <span className="font-semibold" style={{ color: "var(--amber)" }}>
                  {p.avg_confidence !== null ? formatScore(p.avg_confidence) : "—"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No confirmed matches against the library yet.
          </p>
        )}
      </Panel>
    </div>
  );
}
