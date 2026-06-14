"use client";

import { useHealth } from "@/hooks/use-health";
import { cn } from "@/lib/utils";

export function HealthBadge() {
  const { data, isError, isLoading } = useHealth();

  const state = isLoading
    ? { dot: "bg-muted-foreground", label: "Checking…" }
    : isError || !data
      ? { dot: "bg-red-500", label: "Offline" }
      : { dot: "bg-emerald-500", label: "Healthy" };

  return (
    <div className="flex items-center gap-2 rounded-full border px-3 py-1.5">
      <span className={cn("size-2 rounded-full", state.dot)} />
      <span className="text-xs font-medium leading-none">
        <span className="text-muted-foreground">Backend</span> {state.label}
      </span>
    </div>
  );
}
