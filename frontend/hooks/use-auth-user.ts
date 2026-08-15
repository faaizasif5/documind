"use client";

import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

export interface AuthUserInfo {
  name: string | null;
  email: string | null;
}

function readName(metadata: Record<string, unknown> | undefined): string | null {
  const fullName = metadata?.full_name;
  const name = metadata?.name;
  if (typeof fullName === "string" && fullName.trim()) {
    return fullName;
  }
  if (typeof name === "string" && name.trim()) {
    return name;
  }
  return null;
}

/** Tracks the signed-in Supabase user for display in the app shell. */
export function useAuthUser(): AuthUserInfo | null {
  const [user, setUser] = useState<AuthUserInfo | null>(null);

  useEffect(() => {
    const supabase = createClient();
    let active = true;

    const load = async () => {
      const {
        data: { user: sessionUser },
      } = await supabase.auth.getUser();
      if (!active) {
        return;
      }
      setUser(
        sessionUser
          ? {
              name: readName(sessionUser.user_metadata as Record<string, unknown>),
              email: sessionUser.email ?? null,
            }
          : null,
      );
    };

    void load();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      void load();
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  return user;
}

export function authUserLabel(user: AuthUserInfo): string {
  return user.name?.trim() || user.email || "Signed in";
}
