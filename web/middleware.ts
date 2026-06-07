import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE, expectedToken, tokensMatch } from "@/lib/auth";

// Gate everything except the login page, the auth API, and static assets.
// Authed users who hit /login are bounced to the launcher.
export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const cookie = req.cookies.get(AUTH_COOKIE)?.value;
  const authed = tokensMatch(cookie, await expectedToken());

  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    if (authed) {
      return NextResponse.redirect(new URL("/", req.url));
    }
    return NextResponse.next();
  }

  if (!authed) {
    const url = new URL("/login", req.url);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // Run on all paths except Next internals, the login API, and common assets.
  matcher: ["/((?!api/login|_next/static|_next/image|favicon.ico).*)"],
};
