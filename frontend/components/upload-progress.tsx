import { cn } from "@/lib/utils";

interface UploadProgressProps {
  percent: number;
  className?: string;
}

/** Transfer bar for an in-flight upload; flips to indeterminate while the server processes. */
export function UploadProgress({ percent, className }: UploadProgressProps) {
  const transferred = percent >= 100;

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Upload progress"
          style={{ width: `${Math.max(percent, 4)}%` }}
          className={cn(
            "h-full rounded-full bg-primary transition-[width] duration-200",
            transferred && "motion-safe:animate-pulse",
          )}
        />
      </div>
      <p className="text-[11px] text-muted-foreground">
        {transferred ? "Processing document…" : `Uploading… ${percent}%`}
      </p>
    </div>
  );
}
