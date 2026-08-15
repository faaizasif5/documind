"use client";

import { useState } from "react";

import { ChatView } from "@/components/chat-view";
import { DocumentsView } from "@/components/documents-view";
import { Sidebar } from "@/components/sidebar";
import { SidebarRail } from "@/components/sidebar-rail";
import { TopBar } from "@/components/top-bar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { ChatProvider } from "@/hooks/use-chat";
import type { AppView } from "@/lib/views";

export function AppShell() {
  const [view, setView] = useState<AppView>("chat");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <ChatProvider>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        <aside className="hidden shrink-0 border-r lg:flex">
          {collapsed ? (
            <SidebarRail onExpand={() => setCollapsed(false)} />
          ) : (
            <Sidebar onCollapse={() => setCollapsed(true)} />
          )}
        </aside>

        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetContent side="left" className="w-72 p-0">
            <SheetTitle className="sr-only">Documents</SheetTitle>
            <Sidebar onCollapse={() => setSheetOpen(false)} />
          </SheetContent>
        </Sheet>

        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            view={view}
            onSelectView={setView}
            onOpenSheet={() => setSheetOpen(true)}
          />
          <main className="min-h-0 flex-1 overflow-hidden">
            {/* Both views stay mounted so switching never discards the transcript. */}
            <div className={view === "chat" ? "h-full" : "hidden"}>
              <ChatView />
            </div>
            <div className={view === "documents" ? "h-full overflow-y-auto" : "hidden"}>
              <DocumentsView />
            </div>
          </main>
        </div>
      </div>
    </ChatProvider>
  );
}
