"use client";

import { useHealth } from "@/hooks/use-health";
import { cn } from "@/lib/utils";

export function HealthBadge() {
  const { data, isError, isLoading } = useHealth();

  const state = isLoading
    ? { dot: "bg-muted-foreground", label: "Checking…", healthy: false }
    : isError || !data
      ? { dot: "bg-destructive", label: "Offline", healthy: false }
      : { dot: "bg-emerald-500", label: "Healthy", healthy: true };

  return (
    <div
      title={`Backend ${state.label}`}
      className={cn(
        "flex items-center gap-2 rounded-full border px-2.5 py-1",
        state.healthy && "border-transparent",
      )}
    >
      <span className={cn("size-2 rounded-full", state.dot)} />
      {/* Only name the state when it needs attention; healthy is just a dot. */}
      {!state.healthy && (
        <span className="text-xs font-medium leading-none">{state.label}</span>
      )}
      <span className="sr-only">Backend {state.label}</span>
    </div>
  );
}
