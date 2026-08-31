import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE_NAME, verifySessionToken } from "../../../../../auth/session";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";
const SUPPORTED_OUTPUTS = new Set(["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]);

export async function PUT(request: NextRequest, context: { params: Promise<{ outputId: string }> }) {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const session = await verifySessionToken(token, process.env.POOLBERRY_AUTH_SESSION_SECRET);
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  if (session.role !== "ADMIN") return NextResponse.json({ detail: "Admin access required" }, { status: 403 });

  const { outputId: rawOutputId } = await context.params;
  const outputId = rawOutputId.toUpperCase();
  if (!SUPPORTED_OUTPUTS.has(outputId)) return NextResponse.json({ detail: "Unknown output" }, { status: 404 });
  let body: { enabled?: unknown };
  try { body = await request.json(); } catch { return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 }); }
  if (typeof body.enabled !== "boolean") return NextResponse.json({ detail: "enabled must be boolean" }, { status: 422 });
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/outputs/${outputId}/command`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: body.enabled }), cache: "no-store",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch { return NextResponse.json({ detail: "Command service unavailable" }, { status: 503 }); }
}
