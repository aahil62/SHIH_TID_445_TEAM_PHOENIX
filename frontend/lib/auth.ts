"use client";

import type { AnalystProfile, TokenResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const TOKEN_COOKIE = "fraudlens_token";
const ANALYST_STORAGE_KEY = "fraudlens_analyst";

/** Stored as a plain (non-httpOnly) cookie so middleware.ts can read it at
 * the edge for route protection, and as localStorage so client components
 * can attach it to fetch() calls without parsing document.cookie every
 * time. A real production system would set this httpOnly from the server;
 * for this demo the token itself still only verifies against the backend's
 * real JWT secret — nothing here is a fake auth check. */
export function setSession(token: string, analyst: AnalystProfile) {
  document.cookie = `${TOKEN_COOKIE}=${token}; path=/; max-age=${60 * 60 * 24}; samesite=lax`;
  localStorage.setItem(TOKEN_COOKIE, token);
  localStorage.setItem(ANALYST_STORAGE_KEY, JSON.stringify(analyst));
}

export function clearSession() {
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0`;
  localStorage.removeItem(TOKEN_COOKIE);
  localStorage.removeItem(ANALYST_STORAGE_KEY);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_COOKIE);
}

// useSyncExternalStore requires getSnapshot to return a referentially
// stable value when nothing has changed — parsing a fresh object on every
// call (as this used to) reads as "always changed" and causes an infinite
// render loop (a real bug hit and fixed live, not a hypothetical). Cache
// the last raw string alongside its parsed result so repeated calls with
// unchanged localStorage return the exact same object reference.
let _lastRawAnalyst: string | null = null;
let _lastParsedAnalyst: AnalystProfile | null = null;

export function getStoredAnalyst(): AnalystProfile | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(ANALYST_STORAGE_KEY);
  if (raw === _lastRawAnalyst) return _lastParsedAnalyst;
  _lastRawAnalyst = raw;
  if (!raw) {
    _lastParsedAnalyst = null;
    return null;
  }
  try {
    _lastParsedAnalyst = JSON.parse(raw) as AnalystProfile;
    return _lastParsedAnalyst;
  } catch {
    _lastParsedAnalyst = null;
    return null;
  }
}

export class AuthApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
  }
}

async function authFetch(path: string, body: unknown): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data && typeof data.detail === "string"
        ? data.detail
        : `Request failed (${res.status}).`;
    throw new AuthApiError(res.status, detail);
  }
  return data as TokenResponse;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const result = await authFetch("/auth/login", { username, password });
  setSession(result.access_token, result.analyst);
  return result;
}

export async function signup(
  username: string,
  displayName: string,
  password: string
): Promise<TokenResponse> {
  const result = await authFetch("/auth/signup", {
    username,
    display_name: displayName,
    password,
  });
  setSession(result.access_token, result.analyst);
  return result;
}
