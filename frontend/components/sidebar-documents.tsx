"use client";

import { FileText, Loader2, MoreVertical, Trash2 } from "lucide-react";
import { toast } from "sonner";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDeleteDocument, useDocuments } from "@/hooks/use-documents";
import { ApiError } from "@/lib/api";
import type { DocumentResponse, DocumentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<DocumentStatus, string> = {
  ready: "Ready",
  processing: "Processing",
  failed: "Failed",
};

const STATUS_COLOR: Record<DocumentStatus, string> = {
  ready: "text-emerald-600",
  processing: "text-amber-600",
  failed: "text-red-600",
};

function DocumentCard({ document }: { document: DocumentResponse }) {
  const remove = useDeleteDocument();

  return (
    <div className="group flex items-center gap-3 rounded-xl border border-transparent p-2.5 transition-colors hover:border-border hover:bg-accent/40">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-500">
        <FileText className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{document.filename}</p>
        <p className="flex items-center gap-1.5 text-xs">
          <span className={cn("flex items-center font-medium", STATUS_COLOR[document.status])}>
            {document.status === "processing" && (
              <Loader2 className="mr-1 inline size-3 animate-spin" />
            )}
            {STATUS_LABEL[document.status]}
          </span>
          <span className="text-muted-foreground">·</span>
          <span className="text-muted-foreground">
            {document.page_count} {document.page_count === 1 ? "page" : "pages"}
          </span>
        </p>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label={`Actions for ${document.filename}`}
            className="rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-accent group-hover:opacity-100 focus-visible:opacity-100"
          >
            {remove.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <MoreVertical className="size-4" />
            )}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={() =>
              remove.mutate(document.id, {
                onSuccess: () => toast.success(`Deleted "${document.filename}"`),
                onError: (error) =>
                  toast.error(error instanceof ApiError ? error.message : "Delete failed"),
              })
            }
          >
            <Trash2 className="mr-2 size-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

export function SidebarDocuments() {
  const { data, isLoading, isError } = useDocuments();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6 text-xs text-muted-foreground">
        <Loader2 className="mr-2 size-3.5 animate-spin" />
        Loading…
      </div>
    );
  }

  if (isError) {
    return (
      <p className="px-2 py-6 text-center text-xs text-destructive">
        Couldn&apos;t load documents.
      </p>
    );
  }

  if (!data || data.length === 0) {
    return (
      <p className="px-2 py-6 text-center text-xs text-muted-foreground">
        No documents yet. Upload a PDF to get started.
      </p>
    );
  }

  return (
    <div className="space-y-1">
      {data.map((document) => (
        <DocumentCard key={document.id} document={document} />
      ))}
    </div>
  );
}
