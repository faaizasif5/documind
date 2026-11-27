import { processingLabel, processingPercent } from "@/lib/document-status";
import type { DocumentResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

interface IngestionProgressProps {
  document: DocumentResponse;
  className?: string;
}

/** Server-side embedding progress, fed by the existing document polling. */
export function IngestionProgress({ document, className }: IngestionProgressProps) {
  const percent = processingPercent(document);

  return (
    <div className={cn("space-y-1", className)}>
      <div className="h-1 overflow-hidden rounded-full bg-muted">
        <div
          role="progressbar"
          aria-label={`Embedding progress for ${document.filename}`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent ?? undefined}
          style={{ width: `${Math.max(percent ?? 0, 4)}%` }}
          className={cn(
            "h-full rounded-full bg-amber-500 transition-[width] duration-500",
            percent === null && "motion-safe:animate-pulse",
          )}
        />
      </div>
      <p className="text-[11px] tabular-nums text-muted-foreground">{processingLabel(document)}</p>
    </div>
  );
}
