"use client";

import type { ReactNode } from "react";
import { useRef } from "react";

import { cn } from "@/lib/utils";

interface SpotlightCardProps {
  /** Rendered element so this client component stays serializable from the server. */
  icon: ReactNode;
  title: string;
  description: string;
  className?: string;
}

/** Feature card with a cursor-tracked highlight to make hover feel responsive. */
export function SpotlightCard({
  icon,
  title,
  description,
  className,
}: SpotlightCardProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    const node = ref.current;
    if (!node) {
      return;
    }
    const rect = node.getBoundingClientRect();
    node.style.setProperty("--spotlight-x", `${event.clientX - rect.left}px`);
    node.style.setProperty("--spotlight-y", `${event.clientY - rect.top}px`);
  }

  return (
    <div
      ref={ref}
      onPointerMove={handlePointerMove}
      className={cn(
        "group relative overflow-hidden rounded-2xl border bg-card p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5",
        className,
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(18rem circle at var(--spotlight-x, 50%) var(--spotlight-y, 0%), hsl(var(--primary) / 0.10), transparent 65%)",
        }}
      />
      <span className="relative grid size-11 place-items-center rounded-xl bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110">
        {icon}
      </span>
      <h3 className="relative mt-5 font-semibold">{title}</h3>
      <p className="relative mt-2 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </div>
  );
}
