import { createClient, getAccessToken } from "@/lib/supabase/client";

/**
 * Build request headers, optionally requiring a Supabase access token.
 * Does not set Content-Type so multipart uploads keep the browser boundary.
 */
export async function buildApiHeaders(
  init?: HeadersInit,
  options: { requireAuth?: boolean } = {},
): Promise<Headers> {
  const headers = new Headers(init);
  const requireAuth = options.requireAuth ?? true;

  if (!requireAuth) {
    return headers;
  }

  const token = await getAccessToken();
  if (!token) {
    await redirectToLogin();
    throw new AuthRequiredError();
  }

  headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

export class AuthRequiredError extends Error {
  constructor() {
    super("Authentication required");
    this.name = "AuthRequiredError";
  }
}

/** Clear the local session and send the user back to login. */
export async function redirectToLogin(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  const supabase = createClient();
  await supabase.auth.signOut();

  const next = `${window.location.pathname}${window.location.search}`;
  const loginUrl = new URL("/login", window.location.origin);
  loginUrl.searchParams.set("next", next.startsWith("/") ? next : "/");
  window.location.assign(loginUrl.toString());
}
