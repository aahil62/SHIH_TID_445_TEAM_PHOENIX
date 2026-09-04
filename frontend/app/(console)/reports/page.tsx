import Link from "next/link";
import { getReports } from "@/lib/api";
import Panel from "@/components/Panel";
import { formatScore } from "@/lib/risk";

const TONE_COLOR: Record<string, string> = {
  red: "var(--risk-high)",
  amber: "var(--risk-medium)",
  green: "var(--risk-low)",
  blue: "var(--cobalt)",
};

export default async function ReportsPage() {
  const { rows } = await getReports(50);

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Reports
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
          Generate and export structured, masked investigation reports — highest risk first.
        </p>
      </div>

      <Panel title={`${rows.length} cases`}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr
                className="border-b text-left text-[10.5px] font-semibold uppercase tracking-wider"
                style={{ borderColor: "var(--border)", color: "var(--muted)" }}
              >
                <th className="py-2 pr-3">Transaction</th>
                <th className="py-2 pr-3">Risk</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Analyst</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.txn_id} className="hoverable-row border-b" style={{ borderColor: "var(--border)" }}>
                  <td className="py-2.5 pr-3 font-mono text-xs" style={{ color: "var(--foreground)" }}>
                    {r.txn_id}
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-xs font-semibold" style={{ color: TONE_COLOR[r.tone] }}>
                    {formatScore(r.risk_pct)}
                  </td>
                  <td className="py-2.5 pr-3 text-xs capitalize" style={{ color: "var(--foreground)" }}>
                    {r.status.toLowerCase().replace(/_/g, " ")}
                  </td>
                  <td className="py-2.5 pr-3 text-xs" style={{ color: "var(--muted)" }}>{r.analyst}</td>
                  <td className="py-2.5 pr-3 text-xs" style={{ color: "var(--muted)" }}>{r.report_type}</td>
                  <td className="py-2.5 pr-3 text-right text-xs font-semibold">
                    <Link href={`/case?txn_id=${encodeURIComponent(r.txn_id)}`} style={{ color: "var(--cobalt)" }} className="mr-3">
                      View
                    </Link>
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001"}/reports/${encodeURIComponent(r.txn_id)}/pdf`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: "var(--cobalt)" }}
                    >
                      Export PDF
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
