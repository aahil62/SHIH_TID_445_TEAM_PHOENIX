"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/feed", label: "Alert Feed" },
  { href: "/insights", label: "Model Performance" },
];

export default function NavRail() {
  const pathname = usePathname();

  return (
    <nav
      className="flex w-56 shrink-0 flex-col gap-1 px-3 py-4"
      style={{ backgroundColor: "var(--graphite)" }}
    >
      <div className="px-2 pb-4 text-sm font-semibold tracking-wide text-white">
        FraudLens
      </div>
      {LINKS.map((link) => {
        const active = pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className="rounded px-2 py-1.5 text-sm transition-colors"
            style={{
              color: active ? "var(--cobalt-foreground)" : "var(--graphite-foreground)",
              backgroundColor: active ? "var(--cobalt)" : "transparent",
            }}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
