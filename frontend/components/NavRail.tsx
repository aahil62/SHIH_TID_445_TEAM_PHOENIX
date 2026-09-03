"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  {
    href: "/feed",
    label: "Alert Feed",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4 shrink-0" aria-hidden="true">
        <path
          d="M3.5 5.5h13M3.5 10h13M3.5 14.5h8"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
];

export default function NavRail() {
  const pathname = usePathname();

  return (
    <nav
      className="flex w-56 shrink-0 flex-col gap-1 px-3 py-4"
      style={{ backgroundColor: "var(--graphite)" }}
    >
      <div className="mb-6 flex items-center gap-2 px-2">
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

      {LINKS.map((link) => {
        const active = pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className="flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-sm font-medium transition-colors"
            style={{
              color: active ? "var(--cobalt-foreground)" : "var(--graphite-foreground)",
              backgroundColor: active ? "var(--cobalt)" : "transparent",
            }}
          >
            {link.icon}
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
