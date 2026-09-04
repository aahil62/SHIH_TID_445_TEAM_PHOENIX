import { getCases } from "@/lib/api";
import CaseListItem from "@/components/CaseListItem";

export default async function CasesPage() {
  const { cases } = await getCases();
  const sorted = [...cases].sort((a, b) => b.final_score - a.final_score);

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <div className="mb-5 flex items-baseline justify-between">
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
          Investigations
        </h1>
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          {sorted.length} case{sorted.length === 1 ? "" : "s"} on record, highest risk first
        </span>
      </div>

      {sorted.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>
          No cases have been analyzed yet — visit the alert feed to trigger analysis.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {sorted.map((item) => (
            <CaseListItem key={item.txn_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
