"use client";

import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { DocumentIcon } from "@/components/document-icon";
import { Button } from "@/components/ui/button";
import { useDeleteDocument, useDocuments } from "@/hooks/use-documents";
import { ApiError } from "@/lib/api";
import type { DocumentResponse, DocumentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_CLASS: Record<DocumentStatus, string> = {
  ready: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  processing: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  failed: "bg-red-500/10 text-red-600 dark:text-red-400",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DocumentRow({ document }: { document: DocumentResponse }) {
  const remove = useDeleteDocument();

  return (
    <li className="flex items-center gap-3 rounded-xl border p-3">
      <DocumentIcon />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{document.filename}</p>
        <p className="text-xs text-muted-foreground">
          {document.page_count} {document.page_count === 1 ? "page" : "pages"} ·{" "}
          {formatSize(document.file_size)}
        </p>
      </div>
      <span
        className={cn(
          "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium capitalize",
          STATUS_CLASS[document.status],
        )}
      >
        {document.status === "processing" && <Loader2 className="size-3 animate-spin" />}
        {document.status}
      </span>
      <Button
        variant="ghost"
        size="icon"
        className="shrink-0"
        aria-label={`Delete ${document.filename}`}
        disabled={remove.isPending}
        onClick={() =>
          remove.mutate(document.id, {
            onSuccess: () => toast.success(`Deleted "${document.filename}"`),
            onError: (error) =>
              toast.error(error instanceof ApiError ? error.message : "Delete failed"),
          })
        }
      >
        {remove.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Trash2 className="size-4" />
        )}
      </Button>
    </li>
  );
}

export function DocumentList() {
  const { data, isLoading, isError, error } = useDocuments();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
        <Loader2 className="mr-2 size-4 animate-spin" />
        Loading documents…
      </div>
    );
  }

  if (isError) {
    return (
      <p className="py-8 text-center text-sm text-destructive">
        {error instanceof ApiError ? error.message : "Failed to load documents"}
      </p>
    );
  }

  if (!data || data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No documents yet. Upload a PDF to get started.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {data.map((document) => (
        <DocumentRow key={document.id} document={document} />
      ))}
    </ul>
  );
}
