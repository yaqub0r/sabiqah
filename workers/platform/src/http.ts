export function json(value: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("cache-control", "no-store");
  return new Response(JSON.stringify(value), { ...init, headers });
}

export function parseCookies(request: Request): Map<string, string> {
  const cookies = new Map<string, string>();
  for (const pair of (request.headers.get("cookie") ?? "").split(";")) {
    const separator = pair.indexOf("=");
    if (separator < 0) continue;
    cookies.set(
      pair.slice(0, separator).trim(),
      decodeURIComponent(pair.slice(separator + 1).trim()),
    );
  }
  return cookies;
}

export function cookie(
  name: string,
  value: string,
  options: { maxAge: number; path?: string },
): string {
  return [
    `${name}=${encodeURIComponent(value)}`,
    `Max-Age=${options.maxAge}`,
    `Path=${options.path ?? "/"}`,
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
  ].join("; ");
}

export function safeReturnTo(value: unknown): string {
  return typeof value === "string" &&
    value.startsWith("/") &&
    !value.startsWith("//")
    ? value
    : "/works/al-isabah/";
}
