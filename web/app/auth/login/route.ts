import { scryptSync, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import {
  createSessionToken,
  SESSION_COOKIE_NAME,
  SESSION_MAX_AGE_SECONDS,
} from "@/auth/session";

export const runtime = "nodejs";

function verifyPassword(password: string, storedHash: string): boolean {
  const parts = storedHash.split("$");
  if (parts.length !== 3 || parts[0] !== "scrypt") return false;

  const salt = Buffer.from(parts[1], "hex");
  const expected = Buffer.from(parts[2], "hex");
  if (salt.length < 16 || expected.length !== 64) return false;

  const actual = scryptSync(password, salt, expected.length);
  return timingSafeEqual(actual, expected);
}

function safeNextPath(value: FormDataEntryValue | null): string {
  if (typeof value !== "string") return "/";
  if (!value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
}

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const username = String(formData.get("username") ?? "");
  const password = String(formData.get("password") ?? "");
  const nextPath = safeNextPath(formData.get("next"));

  const configuredUsername = process.env.POOLBERRY_AUTH_USERNAME;
  const configuredPasswordHash = process.env.POOLBERRY_AUTH_PASSWORD_SCRYPT;
  const sessionSecret = process.env.POOLBERRY_AUTH_SESSION_SECRET;

  if (!configuredUsername || !configuredPasswordHash || !sessionSecret) {
    return NextResponse.redirect(new URL("/login?error=config", request.url), 303);
  }

  const usernameMatches = username === configuredUsername;
  const passwordMatches = verifyPassword(password, configuredPasswordHash);

  if (!usernameMatches || !passwordMatches) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("error", "credentials");
    if (nextPath !== "/") loginUrl.searchParams.set("next", nextPath);
    return NextResponse.redirect(loginUrl, 303);
  }

  const token = await createSessionToken(configuredUsername, sessionSecret);
  const response = NextResponse.redirect(new URL(nextPath, request.url), 303);
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  });
  return response;
}
