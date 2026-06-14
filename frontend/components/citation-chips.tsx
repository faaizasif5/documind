import { FileText } from "lucide-react";

import type { Source } from "@/lib/types";

export function CitationChips({ sources }: { sources: Source[] }) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {sources.map((source, index) => (
        <span
          key={`${source.document_id}-${source.page_number}`}
          className="inline-flex items-center gap-1.5 rounded-md border bg-accent/60 py-1 pl-1.5 pr-2 text-xs"
        >
          <FileText className="size-3 text-primary" />
          <span className="font-medium text-primary">Source {index + 1}</span>
          <span className="text-muted-foreground">Page {source.page_number}</span>
        </span>
      ))}
    </div>
  );
}
