const encoder = new TextEncoder();
const decoder = new TextDecoder();

export const SESSION_COOKIE_NAME = "poolberry_session";
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export type UserRole = "ADMIN" | "OPERATOR";

export type SessionPayload = {
  username: string;
  role: UserRole;
  expires_at: number;
};

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlToBytes(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function base64UrlEncode(value: string): string { return bytesToBase64Url(encoder.encode(value)); }
function base64UrlDecode(value: string): string { return decoder.decode(base64UrlToBytes(value)); }

async function signingKey(secret: string) {
  return crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

async function sign(value: string, secret: string): Promise<string> {
  const key = await signingKey(secret);
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(value));
  return bytesToBase64Url(new Uint8Array(signature));
}

export async function createSessionToken(username: string, secret: string, role: UserRole = "OPERATOR"): Promise<string> {
  const payload: SessionPayload = { username, role, expires_at: Math.floor(Date.now() / 1000) + SESSION_MAX_AGE_SECONDS };
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  const signature = await sign(encodedPayload, secret);
  return `${encodedPayload}.${signature}`;
}

export async function verifySessionToken(token: string | undefined, secret: string | undefined): Promise<SessionPayload | null> {
  if (!token || !secret) return null;
  const separator = token.lastIndexOf(".");
  if (separator <= 0) return null;
  const encodedPayload = token.slice(0, separator);
  const suppliedSignature = token.slice(separator + 1);
  const expectedSignature = await sign(encodedPayload, secret);
  if (suppliedSignature.length !== expectedSignature.length) return null;
  let mismatch = 0;
  for (let index = 0; index < suppliedSignature.length; index += 1) mismatch |= suppliedSignature.charCodeAt(index) ^ expectedSignature.charCodeAt(index);
  if (mismatch !== 0) return null;
  try {
    const payload = JSON.parse(base64UrlDecode(encodedPayload)) as SessionPayload;
    if (!payload.username || !payload.expires_at) return null;
    if (payload.role !== "ADMIN" && payload.role !== "OPERATOR") return null;
    if (payload.expires_at <= Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch { return null; }
}
