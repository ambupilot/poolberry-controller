import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { SESSION_COOKIE_NAME, verifySessionToken } from "../../../auth/session";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

export const dynamic = "force-dynamic";

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const session = await verifySessionToken(token, process.env.POOLBERRY_AUTH_SESSION_SECRET);
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/output-state`, { cache: "no-store" });
    if (!response.ok) return NextResponse.json({ detail: "Output state unavailable" }, { status: response.status });
    return NextResponse.json(await response.json(), { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "Output state unavailable" }, { status: 503 });
  }
}
