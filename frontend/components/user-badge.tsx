"use client";

import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

interface AuthUserInfo {
  name: string | null;
  email: string | null;
}

function displayName(info: AuthUserInfo): string {
  return info.name?.trim() || info.email || "Signed in";
}

/** Shows the signed-in Google name/email in the app shell. */
export function UserBadge() {
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
      if (!sessionUser) {
        setUser(null);
        return;
      }
      const meta = sessionUser.user_metadata as Record<string, unknown> | undefined;
      const name =
        (typeof meta?.full_name === "string" && meta.full_name) ||
        (typeof meta?.name === "string" && meta.name) ||
        null;
      setUser({
        name,
        email: sessionUser.email ?? null,
      });
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

  if (!user) {
    return null;
  }

  const label = displayName(user);

  return (
    <div className="hidden max-w-[12rem] truncate text-right text-sm sm:block">
      <p className="truncate font-medium leading-tight">{label}</p>
      {user.name && user.email && (
        <p className="truncate text-xs text-muted-foreground">{user.email}</p>
      )}
    </div>
  );
}
