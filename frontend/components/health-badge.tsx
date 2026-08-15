"use client";

import { useHealth } from "@/hooks/use-health";
import { cn } from "@/lib/utils";

export function HealthBadge() {
  const { data, isError, isPending, isFetching } = useHealth();

  const state = data
    ? { dot: "bg-emerald-500", label: "Healthy", healthy: true }
    : isPending || isFetching
      ? { dot: "bg-muted-foreground", label: "Waking…", healthy: false }
      : isError
        ? { dot: "bg-destructive", label: "Offline", healthy: false }
        : { dot: "bg-muted-foreground", label: "Waking…", healthy: false };

  return (
    <div
      title={`Backend ${state.label}`}
      className={cn(
        "flex items-center gap-2 rounded-full border px-2.5 py-1",
        state.healthy && "border-transparent",
      )}
    >
      <span className={cn("size-2 rounded-full", state.dot)} />
      {!state.healthy && (
        <span className="text-xs font-medium leading-none">{state.label}</span>
      )}
      <span className="sr-only">Backend {state.label}</span>
    </div>
  );
}
