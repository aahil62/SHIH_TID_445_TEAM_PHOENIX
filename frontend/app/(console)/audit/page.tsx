import Link from "next/link";
import { getGlobalAudit } from "@/lib/api";
import Panel from "@/components/Panel";
import { formatTimestamp } from "@/lib/risk";

const TONE_COLOR: Record<string, string> = {
  red: "var(--risk-high)",
  amber: "var(--risk-medium)",
  green: "var(--risk-low)",
  blue: "var(--cobalt)",
};

export default async function AuditPage() {
  const { events } = await getGlobalAudit(150);

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Audit Trail
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
          Every analyst decision and system action, logged immutably, across every case.
        </p>
      </div>

      <Panel title={`${events.length} recent events`}>
        <div className="relative pl-5">
          <div
            className="absolute top-1 bottom-4 left-[7px] w-px"
            style={{ backgroundColor: "var(--border)" }}
          />
          <div className="flex flex-col gap-5">
            {events.map((e) => (
              <div key={e.id} className="relative pl-5">
                <div
                  className="absolute top-1 -left-[13px] h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: TONE_COLOR[e.tone] }}
                />
                <div className="mb-0.5 font-mono text-[11px]" style={{ color: "var(--muted)" }}>
                  {formatTimestamp(e.occurred_at)}
                </div>
                <div className="text-sm" style={{ color: "var(--foreground)" }}>
                  {e.text}
                </div>
                {e.txn_id && (
                  <Link
                    href={`/case?txn_id=${encodeURIComponent(e.txn_id)}`}
                    className="text-[11px] font-medium underline-offset-2 hover:underline"
                    style={{ color: "var(--cobalt)" }}
                  >
                    {e.txn_id} →
                  </Link>
                )}
              </div>
            ))}
            {events.length === 0 && (
              <p className="text-sm" style={{ color: "var(--muted)" }}>No audit events yet.</p>
            )}
          </div>
        </div>
      </Panel>
    </div>
  );
}
