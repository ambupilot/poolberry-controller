import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { SESSION_COOKIE_NAME, verifySessionToken } from "../../../auth/session";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

export async function POST() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const session = await verifySessionToken(token, process.env.POOLBERRY_AUTH_SESSION_SECRET);
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/stop`, {
      method: "POST",
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "Stop service unavailable" }, { status: 503 });
  }
}
