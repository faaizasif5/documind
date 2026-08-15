"use client";

import { ChevronDown, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { authUserLabel, useAuthUser } from "@/hooks/use-auth-user";
import { createClient } from "@/lib/supabase/client";

export function UserMenu() {
  const user = useAuthUser();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  if (!user) {
    return null;
  }

  const label = authUserLabel(user);

  const signOut = async () => {
    setSigningOut(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signOut();

    if (error) {
      toast.error("Could not sign out. Please try again.");
      setSigningOut(false);
      return;
    }

    router.replace("/");
    router.refresh();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 rounded-full border py-1 pl-1 pr-2 text-sm transition-colors hover:bg-accent/50">
        <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold uppercase text-primary-foreground">
          {label.slice(0, 1)}
        </span>
        <span className="hidden max-w-[9rem] truncate font-medium sm:block">
          {label}
        </span>
        <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-60">
        <div className="px-2 py-1.5">
          <p className="truncate text-sm font-medium">{label}</p>
          {user.email && user.email !== label && (
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          )}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          disabled={signingOut}
          onClick={() => void signOut()}
          className="text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 size-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
