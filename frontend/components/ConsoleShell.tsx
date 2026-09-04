"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { getHealth } from "@/lib/api";
import { clearSession, getStoredAnalyst } from "@/lib/auth";

const NAV_ITEMS: { label: string; href: string; icon: React.ReactNode }[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
  },
  {
    label: "Live Feed",
    href: "/live",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3.5 2" />
      </>
    ),
  },
  {
    label: "Alerts",
    href: "/feed",
    icon: (
      <>
        <path d="M12 3a5 5 0 0 0-5 5v3.4c0 .5-.16 1-.46 1.4L5 15h14l-1.54-2.2c-.3-.4-.46-.9-.46-1.4V8a5 5 0 0 0-5-5z" />
        <path d="M9.5 18a2.5 2.5 0 0 0 5 0" />
      </>
    ),
  },
  {
    label: "Investigations",
    href: "/cases",
    icon: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="M20 20l-4.8-4.8" />
      </>
    ),
  },
  {
    label: "Fraud Network",
    href: "/network",
    icon: (
      <>
        <circle cx="6" cy="12" r="2.4" />
        <circle cx="18" cy="6" r="2.4" />
        <circle cx="18" cy="18" r="2.4" />
        <path d="M8.2 10.8 15.8 7.2M8.2 13.2l7.6 3.6" />
      </>
    ),
  },
  {
    label: "Fraud DNA",
    href: "/fraud-dna",
    icon: (
      <>
        <circle cx="12" cy="12" r="8.5" />
        <circle cx="12" cy="12" r="5" />
        <circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" />
      </>
    ),
  },
  {
    label: "Reports",
    href: "/reports",
    icon: (
      <>
        <path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
        <path d="M14 3v4h4" />
        <path d="M9 13h6M9 16.5h6" />
      </>
    ),
  },
  {
    label: "Performance",
    href: "/insights",
    icon: (
      <>
        <path d="M4 19V9M11 19V4M18 19v-6" />
      </>
    ),
  },
  {
    label: "Audit Trail",
    href: "/audit",
    icon: (
      <>
        <rect x="5.5" y="4" width="13" height="17" rx="1.5" />
        <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" />
        <path d="M9 11l1.6 1.6L14.5 9" />
        <path d="M9 16.5h6" />
      </>
    ),
  },
];

const BREADCRUMB: Record<string, string> = {
  "/dashboard": "Risk Intelligence",
  "/live": "Live Transaction Feed",
  "/feed": "Alert Feed",
  "/cases": "Investigations",
  "/case": "Investigation",
  "/network": "Fraud Network",
  "/fraud-dna": "Fraud DNA",
  "/reports": "Reports",
  "/insights": "Model Performance",
  "/audit": "Audit Trail",
};

function Logo() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" style={{ color: "var(--cobalt)", flexShrink: 0 }}>
      <path
        d="M12 2.5l7.5 3v6c0 5-3.2 8.4-7.5 10-4.3-1.6-7.5-5-7.5-10v-6z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StatusIndicator() {
  const [status, setStatus] = useState<"checking" | "ok" | "down">("checking");

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
    const interval = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const color = status === "ok" ? "var(--risk-low)" : status === "down" ? "var(--risk-high)" : "var(--muted)";
  const label = status === "ok" ? "SYSTEM OK" : status === "down" ? "SYSTEM DOWN" : "CHECKING…";

  return (
    <span className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wide" style={{ color }}>
      <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-current" aria-hidden="true" />
      {label}
    </span>
  );
}

// No-op subscribe: the stored analyst never changes without a full
// navigation (login/signup/logout all call router.push/refresh), so there's
// no external event to listen for — useSyncExternalStore here exists only
// to read localStorage safely without a hydration mismatch (server always
// has no analyst; the client snapshot is read on mount, not during SSR).
function subscribeNever() {
  return () => {};
}

function AnalystBadge() {
  const router = useRouter();
  const analyst = useSyncExternalStore(subscribeNever, getStoredAnalyst, () => null);

  function handleLogout() {
    clearSession();
    router.push("/login");
    router.refresh();
  }

  if (!analyst) return null;

  return (
    <div className="flex items-center gap-3 pl-4" style={{ borderLeft: "1px solid var(--border)" }}>
      <div
        className="flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-bold"
        style={{ backgroundColor: "rgba(22,163,106,0.16)", color: "var(--cobalt)" }}
      >
        {analyst.display_name.charAt(0)}
      </div>
      <span className="text-xs font-medium" style={{ color: "var(--foreground)" }}>
        {analyst.display_name}
      </span>
      <button
        onClick={handleLogout}
        className="text-xs font-medium"
        style={{ color: "var(--muted)" }}
      >
        Log out
      </button>
    </div>
  );
}

function NavContents({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <>
      <Link href="/" className="mb-5 flex items-center gap-2 px-2 py-1" onClick={onNavigate}>
        <Logo />
        <span className="text-[15px] font-bold text-white">FraudLens</span>
      </Link>

      <div className="flex flex-1 flex-col gap-0.5">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className="flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-sm font-medium transition-colors"
              style={{
                backgroundColor: active ? "rgba(22,163,106,0.16)" : "transparent",
                boxShadow: active ? "inset 2px 0 0 var(--cobalt)" : undefined,
                color: active ? "var(--foreground)" : "var(--graphite-foreground)",
              }}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="shrink-0"
                style={{ color: active ? "var(--cobalt)" : "var(--muted)" }}
              >
                {item.icon}
              </svg>
              <span className="whitespace-nowrap">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </>
  );
}

export default function ConsoleShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  // Close the drawer on navigation — adjusting state during render (the
  // documented React pattern for "reset state when a prop changes")
  // instead of an effect, which would set state synchronously after commit.
  const [lastPathname, setLastPathname] = useState(pathname);
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setMobileNavOpen(false);
  }
  const breadcrumb =
    BREADCRUMB[pathname] ?? (pathname.startsWith("/case") ? "Investigation" : "FraudLens");

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar — always visible at md+ */}
      <nav
        className="sticky top-0 hidden h-screen w-[220px] shrink-0 flex-col gap-1 border-r px-3 py-5 backdrop-blur-2xl md:flex"
        style={{ backgroundColor: "var(--graphite)", borderColor: "var(--border)" }}
      >
        <NavContents pathname={pathname} />
      </nav>

      {/* Mobile drawer — off-canvas, toggled by the header's menu button */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
          onClick={() => setMobileNavOpen(false)}
          aria-hidden="true"
        />
      )}
      <nav
        className="fixed inset-y-0 left-0 z-50 flex h-screen w-[240px] shrink-0 flex-col gap-1 border-r px-3 py-5 backdrop-blur-2xl transition-transform duration-300 ease-out md:hidden"
        style={{
          backgroundColor: "var(--graphite)",
          borderColor: "var(--border)",
          transform: mobileNavOpen ? "translateX(0)" : "translateX(-100%)",
        }}
      >
        <NavContents pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        <div
          className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-4 border-b px-4 backdrop-blur-2xl sm:px-6"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--graphite)" }}
        >
          <button
            onClick={() => setMobileNavOpen(true)}
            className="hover-fill -ml-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-control)] md:hidden"
            style={{ color: "var(--foreground)" }}
            aria-label="Open navigation"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>
          <span className="truncate text-sm font-semibold" style={{ color: "var(--foreground)" }}>
            {breadcrumb}
          </span>
          <div className="ml-auto flex items-center gap-4">
            <StatusIndicator />
            <AnalystBadge />
          </div>
        </div>
        <div
          className="flex items-center gap-2 border-b px-6 py-1.5 text-xs font-medium"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--risk-medium-bg)", color: "var(--risk-medium)" }}
        >
          <svg viewBox="0 0 16 16" fill="none" className="h-3.5 w-3.5 shrink-0" aria-hidden="true">
            <path d="M8 1.5 15 14H1L8 1.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
            <path d="M8 6.5v3.2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
            <circle cx="8" cy="11.6" r="0.9" fill="currentColor" />
          </svg>
          Sample workspace — synthetic data, not a production system
        </div>
        <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
