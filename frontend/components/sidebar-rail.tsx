"use client";

import { ChevronsRight, Plus, Sparkles } from "lucide-react";

import { NAV_ITEMS } from "@/components/sidebar";
import { Button } from "@/components/ui/button";
import { useUpload } from "@/hooks/use-upload";
import type { AppView } from "@/lib/views";
import { cn } from "@/lib/utils";

interface SidebarRailProps {
  view: AppView;
  onSelectView: (view: AppView) => void;
  onExpand: () => void;
}

export function SidebarRail({ view, onSelectView, onExpand }: SidebarRailProps) {
  const { getInputProps, open, isPending } = useUpload();

  return (
    <div className="flex h-full w-16 flex-col items-center gap-1 bg-background py-4">
      <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 via-indigo-500 to-blue-500 text-white shadow-sm">
        <Sparkles className="size-5" />
      </div>

      <Button
        variant="ghost"
        size="icon"
        className="mt-1 size-9 text-muted-foreground"
        aria-label="Expand sidebar"
        title="Expand sidebar"
        onClick={onExpand}
      >
        <ChevronsRight className="size-4" />
      </Button>

      <nav className="mt-3 flex flex-col items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const active = view === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectView(item.id)}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
              title={item.label}
              className={cn(
                "flex size-10 items-center justify-center rounded-lg transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              <item.icon className="size-5" />
            </button>
          );
        })}
      </nav>

      <input {...getInputProps()} />
      <Button
        size="icon"
        className="mt-3 size-10 rounded-lg"
        aria-label="Upload PDF"
        title="Upload PDF"
        disabled={isPending}
        onClick={open}
      >
        <Plus className="size-5" />
      </Button>

      <div className="mt-auto flex size-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
        U
      </div>
    </div>
  );
}
