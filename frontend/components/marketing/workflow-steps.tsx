"use client";

import { Quote } from "lucide-react";
import { useEffect, useState } from "react";

import {
  WORKFLOW_AUTO_ADVANCE_MS,
  WORKFLOW_STEPS,
} from "@/lib/marketing-content";
import { cn } from "@/lib/utils";

export function WorkflowSteps() {
  const [active, setActive] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);

  useEffect(() => {
    if (!autoPlay) {
      return;
    }
    const timer = setTimeout(
      () => setActive((current) => (current + 1) % WORKFLOW_STEPS.length),
      WORKFLOW_AUTO_ADVANCE_MS,
    );
    return () => clearTimeout(timer);
  }, [active, autoPlay]);

  const current = WORKFLOW_STEPS[active];

  return (
    <div className="grid gap-8 lg:grid-cols-2 lg:gap-14">
      <ol className="space-y-3">
        {WORKFLOW_STEPS.map(({ icon: Icon, title, description }, index) => {
          const isActive = index === active;
          return (
            <li key={title}>
              <button
                type="button"
                onClick={() => {
                  setAutoPlay(false);
                  setActive(index);
                }}
                className={cn(
                  "flex w-full gap-4 rounded-2xl border p-4 text-left transition-all duration-300 sm:p-5",
                  isActive
                    ? "border-primary/30 bg-card shadow-lg shadow-primary/5"
                    : "border-transparent hover:bg-muted/50",
                )}
              >
                <span
                  className={cn(
                    "relative grid size-11 shrink-0 place-items-center rounded-xl transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  <Icon className="size-5" />
                  {isActive && (
                    <span className="absolute inset-0 rounded-xl bg-primary motion-safe:animate-pulse-ring" />
                  )}
                </span>
                <span className="min-w-0">
                  <span className="text-xs font-medium text-primary">
                    Step 0{index + 1}
                  </span>
                  <span className="mt-0.5 block font-semibold">{title}</span>
                  <span
                    className={cn(
                      "mt-1 block text-sm leading-6 text-muted-foreground transition-all",
                      isActive ? "opacity-100" : "hidden sm:block sm:opacity-70",
                    )}
                  >
                    {description}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-muted/50 to-background p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-10 -top-10 size-40 rounded-full bg-primary/10 blur-2xl" />
        <div key={active} className="motion-safe:animate-fade-up">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {current.title}
          </p>
          <div className="mt-5 space-y-3">
            {current.details.map(({ icon: DetailIcon, label, meta }) => (
              <div
                key={label}
                className="flex items-center gap-3 rounded-xl border bg-background/80 p-3.5 shadow-sm backdrop-blur"
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                  <DetailIcon className="size-4" />
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">
                    {label}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {meta}
                  </span>
                </span>
              </div>
            ))}
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs text-muted-foreground">
            <Quote className="size-3.5 text-primary" />
            Every step keeps the answer traceable to its source.
          </div>
        </div>
      </div>
    </div>
  );
}
