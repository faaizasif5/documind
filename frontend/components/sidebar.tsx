"use client";

import { ChevronsLeft, Plus } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { SidebarDocuments } from "@/components/sidebar-documents";
import { UploadProgress } from "@/components/upload-progress";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUpload } from "@/hooks/use-upload";

export function Sidebar({ onCollapse }: { onCollapse: () => void }) {
  const { getInputProps, open, isPending, progress } = useUpload();

  return (
    <div className="flex h-full w-72 flex-col bg-muted/25">
      <div className="flex items-center justify-between p-4">
        <BrandMark />
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

      <div className="px-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Your Documents
          </span>
          <input {...getInputProps()} />
          <Button
            size="sm"
            className="h-7 gap-1 px-2.5"
            disabled={isPending}
            onClick={open}
          >
            <Plus className="size-3.5" />
            Upload
          </Button>
        </div>
        {isPending && <UploadProgress percent={progress} className="mt-3" />}
      </div>

      <ScrollArea className="mt-2 flex-1 px-2">
        <SidebarDocuments />
      </ScrollArea>
    </div>
  );
}
