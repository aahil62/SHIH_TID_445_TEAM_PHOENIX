import Panel from "@/components/Panel";
import { getPerformanceStats } from "@/lib/api";
import { formatScore } from "@/lib/risk";
import type { AgentPerformance } from "@/lib/types";

function formatMs(value: number): string {
  return `${value.toFixed(2)} ms`;
}

function MetricRow({
  name,
  metrics,
  highlighted,
}: {
  name: string;
  metrics: AgentPerformance;
  highlighted?: boolean;
}) {
  return (
    <tr
      className="border-b last:border-b-0"
      style={{
        borderColor: "var(--border)",
        backgroundColor: highlighted ? "rgba(41, 84, 224, 0.08)" : undefined,
      }}
    >
      <td
        className="px-4 py-2.5 align-top text-sm capitalize"
        style={{
          fontWeight: highlighted ? 600 : 400,
          color: highlighted ? "var(--cobalt)" : "var(--foreground)",
        }}
      >
        {name.replace(/_/g, " ")}
      </td>
      <td className="px-4 py-2.5 align-top font-mono text-xs">{formatScore(metrics.precision)}</td>
      <td className="px-4 py-2.5 align-top font-mono text-xs">{formatScore(metrics.recall)}</td>
      <td className="px-4 py-2.5 align-top font-mono text-xs">{formatScore(metrics.f1)}</td>
      <td className="px-4 py-2.5 align-top font-mono text-xs">{formatScore(metrics.auc_pr)}</td>
      <td className="px-4 py-2.5 align-top font-mono text-xs" style={{ color: "var(--muted)" }}>
        {formatMs(metrics.avg_latency_ms)}
      </td>
    </tr>
  );
}

export default async function InsightsPage() {
  let stats;
  try {
    stats = await getPerformanceStats();
  } catch {
    return (
      <div className="mx-auto max-w-4xl px-6 py-6">
        <p style={{ color: "var(--risk-high)" }}>Couldn&apos;t load model performance data.</p>
      </div>
    );
  }

  const { dataset, agents, ensemble, ml_feature_importances, external_validation } = stats;
  const topFeatures = Object.entries(ml_feature_importances).sort((a, b) => b[1] - a[1]);
  const maxImportance = topFeatures.length > 0 ? topFeatures[0][1] : 1;

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <div className="mb-4 flex items-baseline justify-between">
        <h1 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>
          Model Performance
        </h1>
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          Held-out test: {dataset.test} of {dataset.total} transactions (
          {formatScore(dataset.fraud_ratio_test)} fraud)
        </span>
      </div>

      <div className="flex flex-col gap-4">
        <Panel title="Agent comparison">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] border-collapse text-sm">
              <thead>
                <tr
                  className="border-b text-left text-xs uppercase tracking-wide"
                  style={{ borderColor: "var(--border)", color: "var(--muted)" }}
                >
                  <th className="px-4 py-2 font-medium">Agent</th>
                  <th className="px-4 py-2 font-medium">Precision</th>
                  <th className="px-4 py-2 font-medium">Recall</th>
                  <th className="px-4 py-2 font-medium">F1</th>
                  <th className="px-4 py-2 font-medium">AUC-PR</th>
                  <th className="px-4 py-2 font-medium">Avg latency</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(agents).map(([name, metrics]) => (
                  <MetricRow key={name} name={name} metrics={metrics} />
                ))}
                <MetricRow name="ensemble" metrics={ensemble} highlighted />
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
            Ensemble combines every agent above — highlighted row.
          </p>
        </Panel>

        <Panel title="What the trained model weighs">
          {topFeatures.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No feature importances available.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {topFeatures.map(([feature, importance]) => (
                <div key={feature} className="flex items-center gap-3">
                  <span className="w-36 shrink-0 text-xs capitalize" style={{ color: "var(--foreground)" }}>
                    {feature.replace(/_/g, " ")}
                  </span>
                  <div className="h-2 flex-1 rounded-full" style={{ backgroundColor: "var(--border)" }}>
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${Math.max(2, (importance / maxImportance) * 100)}%`,
                        backgroundColor: "var(--cobalt)",
                      }}
                    />
                  </div>
                  <span className="w-12 shrink-0 text-right font-mono text-xs" style={{ color: "var(--muted)" }}>
                    {formatScore(importance)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="External validation">
          <div
            className="mb-3 inline-flex items-center gap-2 rounded px-2 py-1 text-xs font-medium"
            style={{ color: "var(--risk-medium)", backgroundColor: "var(--risk-medium-bg)" }}
          >
            Real published dataset — not this product&apos;s live data
          </div>
          {external_validation === null ? (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              External validation hasn&apos;t been run on this environment — the source dataset
              (~140MB, third-party licensed) isn&apos;t bundled here. See
              fraudlens/evaluation/validate_ulb.py.
            </p>
          ) : (
            <>
              <p className="mb-3 text-sm" style={{ color: "var(--foreground)" }}>
                Same modeling approach (gradient-boosted, class-balanced) evaluated on{" "}
                {external_validation.dataset}: {external_validation.total_rows.toLocaleString()} real
                transactions, {formatScore(external_validation.fraud_rate)} fraud rate.
              </p>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-4">
                <div>
                  <dt style={{ color: "var(--muted)" }}>Precision</dt>
                  <dd className="font-mono">{formatScore(external_validation.precision)}</dd>
                </div>
                <div>
                  <dt style={{ color: "var(--muted)" }}>Recall</dt>
                  <dd className="font-mono">{formatScore(external_validation.recall)}</dd>
                </div>
                <div>
                  <dt style={{ color: "var(--muted)" }}>F1</dt>
                  <dd className="font-mono">{formatScore(external_validation.f1)}</dd>
                </div>
                <div>
                  <dt style={{ color: "var(--muted)" }}>AUC-PR</dt>
                  <dd className="font-mono">{formatScore(external_validation.auc_pr)}</dd>
                </div>
              </dl>
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}
