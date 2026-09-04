import { NextRequest, NextResponse } from "next/server";

const TOKEN_COOKIE = "fraudlens_token";
const PUBLIC_PATHS = ["/", "/login", "/signup"];

/** Gates every analyst-console page behind a session cookie set at login
 * (see lib/auth.ts's setSession). The landing page and auth pages stay
 * public — everything else (dashboard, feed, case, cases, network,
 * fraud-dna, reports, audit, insights) redirects to /login without a
 * valid-looking session. The token itself is still verified for real by
 * the backend on every write (see fraudlens/api/deps.py) — this
 * middleware only keeps a logged-out visitor from landing on analyst
 * pages in the first place. */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next();
  }

  const token = request.cookies.get(TOKEN_COOKIE)?.value;
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
