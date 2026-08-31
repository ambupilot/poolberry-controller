const encoder = new TextEncoder();

export const SESSION_COOKIE_NAME = "poolberry_session";
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

type SessionPayload = {
  username: string;
  expires_at: number;
};

function base64UrlEncode(value: string): string {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(value, "utf8").toString("base64url");
  }

  const bytes = encoder.encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlDecode(value: string): string {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(value, "base64url").toString("utf8");
  }

  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

async function signingKey(secret: string) {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

async function sign(value: string, secret: string): Promise<string> {
  const key = await signingKey(secret);
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(value));
  const bytes = new Uint8Array(signature);

  if (typeof Buffer !== "undefined") {
    return Buffer.from(bytes).toString("base64url");
  }

  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export async function createSessionToken(username: string, secret: string): Promise<string> {
  const payload: SessionPayload = {
    username,
    expires_at: Math.floor(Date.now() / 1000) + SESSION_MAX_AGE_SECONDS,
  };
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
  for (let index = 0; index < suppliedSignature.length; index += 1) {
    mismatch |= suppliedSignature.charCodeAt(index) ^ expectedSignature.charCodeAt(index);
  }
  if (mismatch !== 0) return null;

  try {
    const payload = JSON.parse(base64UrlDecode(encodedPayload)) as SessionPayload;
    if (!payload.username || !payload.expires_at) return null;
    if (payload.expires_at <= Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}
