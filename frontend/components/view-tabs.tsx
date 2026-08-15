"use client";

import { APP_VIEWS, type AppView } from "@/lib/views";
import { cn } from "@/lib/utils";

interface ViewTabsProps {
  view: AppView;
  onSelectView: (view: AppView) => void;
}

/** Compact segmented switch between the chat and document library. */
export function ViewTabs({ view, onSelectView }: ViewTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Workspace views"
      className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5"
    >
      {APP_VIEWS.map((item) => {
        const active = view === item.id;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onSelectView(item.id)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <item.icon className="size-3.5" />
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
