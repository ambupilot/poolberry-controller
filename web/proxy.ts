import { NextRequest, NextResponse } from "next/server";
import { publicUrl } from "./auth/origin";
import { SESSION_COOKIE_NAME, verifySessionToken } from "./auth/session";

const PUBLIC_PATHS = new Set(["/login", "/auth/login", "/auth/logout"]);

export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (PUBLIC_PATHS.has(pathname)) {
    if (pathname === "/login") {
      const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
      const session = await verifySessionToken(token, process.env.POOLBERRY_AUTH_SESSION_SECRET);
      if (session) return NextResponse.redirect(publicUrl("/"));
    }
    return NextResponse.next();
  }
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  const session = await verifySessionToken(token, process.env.POOLBERRY_AUTH_SESSION_SECRET);
  if (!session) {
    const loginUrl = publicUrl("/login");
    const requestedPath = `${pathname}${search}`;
    if (requestedPath !== "/") loginUrl.searchParams.set("next", requestedPath);
    return NextResponse.redirect(loginUrl);
  }
  if ((pathname === "/hardware" || pathname.startsWith("/hardware/") || pathname.startsWith("/browser-api/outputs/")) && session.role !== "ADMIN") {
    return NextResponse.redirect(publicUrl("/"));
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
