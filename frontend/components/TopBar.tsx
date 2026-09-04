"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

type Status = "checking" | "ok" | "down";

const POLL_INTERVAL_MS = 30_000;

export default function TopBar() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const health = await getHealth();
        if (!cancelled) setStatus(health.status === "ok" ? "ok" : "down");
      } catch {
        if (!cancelled) setStatus("down");
      }
    }

    check();
    const interval = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const statusColor =
    status === "ok" ? "var(--risk-low)" : status === "down" ? "var(--risk-high)" : "var(--muted)";
  const statusLabel = status === "ok" ? "SYSTEM OK" : status === "down" ? "SYSTEM DOWN" : "CHECKING…";

  return (
    <div
      className="flex h-9 shrink-0 items-center justify-between border-b px-4 text-xs"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--graphite)" }}
    >
      <span className="font-semibold tracking-widest text-white">
        FRAUDLENS <span style={{ color: "var(--graphite-foreground)" }}>/ FINANCIAL CRIME OPERATIONS</span>
      </span>
      <span className="flex items-center gap-1.5 font-semibold tracking-wide" style={{ color: statusColor }}>
        <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-current" aria-hidden="true" />
        {statusLabel}
      </span>
    </div>
  );
}
