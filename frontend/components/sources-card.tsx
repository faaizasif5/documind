"use client";

import { ChevronDown, FileText } from "lucide-react";
import { useState } from "react";

import type { Source } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SourcesCard({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) {
    return null;
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        className="flex items-center gap-1.5 rounded-md px-1 py-0.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronDown
          className={cn("size-3.5 transition-transform", expanded && "rotate-180")}
        />
        {sources.length} {sources.length === 1 ? "source" : "sources"}
      </button>

      {expanded && (
        <ul className="mt-1 space-y-1 rounded-xl border bg-card p-2 shadow-sm">
          {sources.map((source) => (
            <li
              key={`${source.document_id}-${source.page_number}`}
              className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-accent/40"
            >
              <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
                <FileText className="size-3.5" />
              </div>
              <span className="min-w-0 flex-1 truncate text-sm font-medium">
                {source.filename}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                Page {source.page_number}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
