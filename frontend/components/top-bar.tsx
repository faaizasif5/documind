"use client";

import { Menu } from "lucide-react";

import { HealthBadge } from "@/components/health-badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { UserMenu } from "@/components/user-menu";
import { ViewTabs } from "@/components/view-tabs";
import type { AppView } from "@/lib/views";

interface TopBarProps {
  view: AppView;
  onSelectView: (view: AppView) => void;
  onOpenSheet: () => void;
}

export function TopBar({ view, onSelectView, onOpenSheet }: TopBarProps) {
  return (
    <header className="z-20 flex h-14 shrink-0 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-xl sm:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="shrink-0 lg:hidden"
        aria-label="Open menu"
        onClick={onOpenSheet}
      >
        <Menu className="size-5" />
      </Button>

      <ViewTabs view={view} onSelectView={onSelectView} />

      <div className="ml-auto flex shrink-0 items-center gap-2">
        <HealthBadge />
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
