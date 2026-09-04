"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/** OVERVIEW (real aggregate stats, GET /cases), CASES, ALERTS, and
 * PERFORMANCE (/insights) are backed by real API data — see
 * DESIGN-AUDIT.md's 2026-09-04 addendum. The rest render as visually
 * present but disabled "coming soon" — never linked to fabricated
 * content. */
const SECTIONS: { label: string; href: string | null }[] = [
  { label: "OVERVIEW", href: "/overview" },
  { label: "CASES", href: "/cases" },
  { label: "ALERTS", href: "/feed" },
  { label: "PERFORMANCE", href: "/insights" },
  { label: "GRAPH", href: null },
  { label: "ENTITIES", href: null },
  { label: "PATTERNS", href: null },
];

export default function NavRail() {
  const pathname = usePathname();

  return (
    <nav
      className="flex w-56 shrink-0 flex-col gap-1 px-3 py-4"
      style={{ backgroundColor: "var(--graphite)" }}
    >
      <div className="mb-3 flex items-center gap-2 px-2">
        <svg viewBox="0 0 24 24" className="h-6 w-6 shrink-0" aria-hidden="true">
          <circle cx="10" cy="10" r="6.5" fill="none" stroke="var(--cobalt)" strokeWidth="2" />
          <circle cx="10" cy="10" r="2.25" fill="var(--cobalt)" />
          <line
            x1="14.8"
            y1="14.8"
            x2="20"
            y2="20"
            stroke="var(--cobalt)"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
        <span className="text-sm font-semibold tracking-wide text-white">FraudLens</span>
      </div>

      {SECTIONS.map((section) => {
        if (section.href === null) {
          return (
            <div
              key={section.label}
              className="flex items-center justify-between rounded-[var(--radius-control)] px-2.5 py-2 text-sm font-medium"
              style={{ color: "var(--graphite-foreground)", opacity: 0.45 }}
              aria-disabled="true"
            >
              <span className="tracking-wide">{section.label}</span>
              <span className="text-[9px] font-semibold tracking-wide">SOON</span>
            </div>
          );
        }

        const active = pathname.startsWith(section.href);
        return (
          <Link
            key={section.href}
            href={section.href}
            className="rounded-[var(--radius-control)] px-2.5 py-2 text-sm font-medium tracking-wide transition-colors"
            style={{
              color: active ? "var(--cobalt-foreground)" : "var(--graphite-foreground)",
              backgroundColor: active ? "var(--cobalt)" : "transparent",
            }}
          >
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
