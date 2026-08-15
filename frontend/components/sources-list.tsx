"use client";

import { FileText } from "lucide-react";

import type { Source } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SourcesListProps {
  sources: Source[];
  /** Scopes anchor ids so inline markers only target this message's list. */
  messageId: string;
  /** Source number highlighted after its inline marker was clicked. */
  highlighted: number | null;
}

export function sourceAnchorId(messageId: string, sourceNumber: number): string {
  return `${messageId}-source-${sourceNumber}`;
}

export function SourcesList({ sources, messageId, highlighted }: SourcesListProps) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <section className="mt-4 rounded-xl border bg-muted/30 p-3">
      <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {sources.length === 1 ? "1 source" : `${sources.length} sources`}
      </h4>
      <ol className="space-y-1">
        {sources.map((source) => {
          const isHighlighted = highlighted === source.number;
          return (
            <li
              key={`${source.document_id}-${source.page_number}`}
              id={sourceAnchorId(messageId, source.number)}
              className={cn(
                "flex items-center gap-2.5 rounded-lg border border-transparent px-2 py-1.5 transition-colors",
                isHighlighted ? "border-primary/40 bg-primary/10" : "hover:bg-background",
              )}
            >
              <span
                className={cn(
                  "grid size-5 shrink-0 place-items-center rounded text-[11px] font-semibold",
                  isHighlighted
                    ? "bg-primary text-primary-foreground"
                    : "bg-primary/10 text-primary",
                )}
              >
                {source.number}
              </span>
              <FileText className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate text-xs font-medium">
                {source.filename}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                Page {source.page_number}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
