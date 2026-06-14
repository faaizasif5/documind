"use client";

import { ChevronsLeft, FileText, MessageSquare, Plus, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { SidebarDocuments } from "@/components/sidebar-documents";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUpload } from "@/hooks/use-upload";
import type { AppView } from "@/lib/views";
import { cn } from "@/lib/utils";

export const NAV_ITEMS: { id: AppView; label: string; icon: LucideIcon }[] = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "documents", label: "Documents", icon: FileText },
];

interface SidebarProps {
  view: AppView;
  onSelectView: (view: AppView) => void;
  onCollapse: () => void;
}

export function Sidebar({ view, onSelectView, onCollapse }: SidebarProps) {
  const { getInputProps, open, isPending } = useUpload();

  return (
    <div className="flex h-full w-72 flex-col bg-background">
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 via-indigo-500 to-blue-500 text-white shadow-sm">
            <Sparkles className="size-5" />
          </div>
          <span className="text-lg font-semibold tracking-tight">DocuMind</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 text-muted-foreground"
          aria-label="Collapse sidebar"
          onClick={onCollapse}
        >
          <ChevronsLeft className="size-4" />
        </Button>
      </div>

      <nav className="space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = view === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectView(item.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              <item.icon className="size-4" />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="mt-6 flex items-center justify-between px-5">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Your Documents
        </span>
        <input {...getInputProps()} />
        <Button size="sm" className="h-7 gap-1 px-2.5" disabled={isPending} onClick={open}>
          <Plus className="size-3.5" />
          Upload
        </Button>
      </div>

      <ScrollArea className="mt-2 flex-1 px-3">
        <SidebarDocuments />
      </ScrollArea>

      <div className="p-3">
        <div className="flex items-start gap-3 rounded-xl bg-accent/60 p-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-500 text-white">
            <Sparkles className="size-4" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium">DocuMind</p>
            <p className="text-xs text-muted-foreground">
              Your AI-powered document assistant
            </p>
          </div>
          <span className="ml-auto shrink-0 text-[10px] text-muted-foreground">v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
