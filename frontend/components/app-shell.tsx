"use client";

import { useState } from "react";

import { ChatView } from "@/components/chat-view";
import { DocumentsView } from "@/components/documents-view";
import { Sidebar } from "@/components/sidebar";
import { SidebarRail } from "@/components/sidebar-rail";
import { TopBar } from "@/components/top-bar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import type { AppView } from "@/lib/views";

const VIEW_HEADERS: Record<AppView, { title: string; subtitle: string }> = {
  chat: {
    title: "Ask a question about your documents",
    subtitle: "Get AI-powered answers with citations from your documents.",
  },
  documents: {
    title: "Documents",
    subtitle: "Upload PDFs and manage your document library.",
  },
};

export function AppShell() {
  const [view, setView] = useState<AppView>("chat");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const header = VIEW_HEADERS[view];

  const selectFromSheet = (next: AppView) => {
    setView(next);
    setSheetOpen(false);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <aside className="hidden shrink-0 border-r lg:flex">
        {collapsed ? (
          <SidebarRail
            view={view}
            onSelectView={setView}
            onExpand={() => setCollapsed(false)}
          />
        ) : (
          <Sidebar
            view={view}
            onSelectView={setView}
            onCollapse={() => setCollapsed(true)}
          />
        )}
      </aside>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Sidebar
            view={view}
            onSelectView={selectFromSheet}
            onCollapse={() => setSheetOpen(false)}
          />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          title={header.title}
          subtitle={header.subtitle}
          onOpenSheet={() => setSheetOpen(true)}
        />
        <main className="min-h-0 flex-1 overflow-hidden">
          {view === "chat" && <ChatView />}
          {view === "documents" && (
            <div className="h-full overflow-y-auto">
              <DocumentsView />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
