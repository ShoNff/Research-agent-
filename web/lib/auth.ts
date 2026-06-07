// Shared auth helpers for the password gate.
//
// The password is only ever read on the server (from APP_PASSWORD, falling back
// to "Lithium3"). We never ship it to the browser. The auth cookie stores a
// SHA-256 hash of the password so it can't be trivially forged without knowing
// the password. Middleware and the login route both derive the expected token
// from the same secret, so they always agree.

export const AUTH_COOKIE = "ra_auth";

/** The configured password (server-side only). */
export function getPassword(): string {
  return process.env.APP_PASSWORD ?? "Lithium3";
}

/** SHA-256 hex digest of an arbitrary string, using Web Crypto (edge-safe). */
async function sha256Hex(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** The cookie value a valid session must carry. */
export function expectedToken(): Promise<string> {
  // Namespace the hash so a bare password hash from elsewhere can't be reused.
  return sha256Hex(`ra-launcher:${getPassword()}`);
}

/** Constant-time-ish comparison of two equal-length tokens. */
export function tokensMatch(a: string | undefined, b: string): boolean {
  if (!a || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
