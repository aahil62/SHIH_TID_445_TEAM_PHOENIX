"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthApiError, signup } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signup(username.trim().toLowerCase(), displayName.trim(), password);
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Couldn't reach the server. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6" style={{ color: "var(--foreground)" }}>
      <div
        className="w-full max-w-sm rounded-[var(--radius-panel)] border p-7 backdrop-blur-xl"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)", boxShadow: "var(--shadow-panel-raised)" }}
      >
        <div className="mb-6 flex items-center gap-2">
          <svg width="20" height="20" viewBox="0 0 24 24" style={{ color: "var(--cobalt)" }}>
            <path
              d="M12 2.5l7.5 3v6c0 5-3.2 8.4-7.5 10-4.3-1.6-7.5-5-7.5-10v-6z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-base font-bold">FraudLens</span>
        </div>
        <h1 className="mb-1 text-lg font-semibold">Create analyst account</h1>
        <p className="mb-6 text-sm" style={{ color: "var(--muted)" }}>
          Every decision you record will be attributed to this account.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Full name (e.g. N. Verma)"
            required
            className="rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--panel-solid)" }}
          />
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            autoComplete="username"
            required
            className="rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--panel-solid)" }}
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Password (min. 6 characters)"
            autoComplete="new-password"
            minLength={6}
            required
            className="rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--panel-solid)" }}
          />
          {error && (
            <p className="text-xs font-medium" style={{ color: "var(--risk-high)" }}>
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="mt-1 rounded-[var(--radius-control)] px-4 py-2.5 text-sm font-semibold transition-opacity disabled:opacity-60"
            style={{ backgroundColor: "var(--cobalt)", color: "var(--cobalt-foreground)" }}
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-5 text-center text-xs" style={{ color: "var(--muted)" }}>
          Already have an account? <Link href="/login" style={{ color: "var(--cobalt)" }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
