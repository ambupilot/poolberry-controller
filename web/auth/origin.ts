export function publicOrigin(): string {
  const configured = process.env.POOLBERRY_PUBLIC_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  return "https://config.kerssing.nl";
}

export function publicUrl(path: string): URL {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return new URL(normalizedPath, `${publicOrigin()}/`);
}
