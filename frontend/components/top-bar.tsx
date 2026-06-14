"use client";

import { Menu } from "lucide-react";

import { HealthBadge } from "@/components/health-badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

interface TopBarProps {
  title: string;
  subtitle?: string;
  onOpenSheet: () => void;
}

export function TopBar({ title, subtitle, onOpenSheet }: TopBarProps) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b px-4 sm:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="shrink-0 lg:hidden"
        aria-label="Open menu"
        onClick={onOpenSheet}
      >
        <Menu className="size-5" />
      </Button>

      <div className="min-w-0">
        <h1 className="truncate text-base font-semibold tracking-tight sm:text-lg">
          {title}
        </h1>
        {subtitle && (
          <p className="hidden truncate text-sm text-muted-foreground sm:block">
            {subtitle}
          </p>
        )}
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-2">
        <HealthBadge />
        <ThemeToggle />
      </div>
    </header>
  );
}
