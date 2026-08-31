import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE_NAME, verifySessionToken } from "../../../auth/session";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

async function getSession() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  return verifySessionToken(token, process.env.POOLBERRY_AUTH_SESSION_SECRET);
}

export async function GET() {
  if (!(await getSession())) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/mode`, { cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "Mode service unavailable" }, { status: 503 });
  }
}

export async function PUT(request: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  if (session.role !== "ADMIN") return NextResponse.json({ detail: "Admin access required" }, { status: 403 });
  let body: { mode?: unknown };
  try { body = await request.json(); }
  catch { return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 }); }
  if (body.mode !== "NORMAL" && body.mode !== "MANUAL") {
    return NextResponse.json({ detail: "Unknown mode" }, { status: 422 });
  }
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/mode`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: body.mode }),
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "Mode service unavailable" }, { status: 503 });
  }
}
