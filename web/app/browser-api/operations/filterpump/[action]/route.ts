import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE_NAME, verifySessionToken } from "../../../../../../auth/session";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ action: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const session = await verifySessionToken(token, process.env.POOLBERRY_AUTH_SESSION_SECRET);
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

  const { action: rawAction } = await context.params;
  const action = rawAction.toLowerCase();
  if (action !== "on" && action !== "off") {
    return NextResponse.json({ detail: "Unknown filter pump action" }, { status: 404 });
  }

  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/operations/filterpump/${action}`, {
      method: "POST",
      cache: "no-store",
    });
    const data = await response.json();
    return NextResponse.json(data, {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "Filter pump operation service unavailable" }, { status: 503 });
  }
}
