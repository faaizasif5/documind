import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

import { getSupabaseEnv } from "@/lib/supabase/env";

/**
 * Server Supabase client for Server Components, Route Handlers, and Server Actions.
 * Cookie writes from Server Components may no-op; middleware refreshes the session.
 */
export function createClient() {
  const cookieStore = cookies();
  const { url, publishableKey } = getSupabaseEnv();

  return createServerClient(url, publishableKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        } catch {
          // Called from a Server Component — middleware owns session refresh.
        }
      },
    },
  });
}
