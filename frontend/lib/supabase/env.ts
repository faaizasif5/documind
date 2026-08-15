/**
 * Shared Supabase public env for browser + server clients.
 * Use the Publishable key from Supabase → Settings → API Keys.
 */
export function getSupabaseEnv(): { url: string; publishableKey: string } {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!url || !publishableKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY. " +
        "Copy frontend/.env.local.example to .env.local and fill in your Supabase project values.",
    );
  }

  return { url, publishableKey };
}
