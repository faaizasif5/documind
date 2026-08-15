import { FileText } from "lucide-react";

import { cn } from "@/lib/utils";

/** PDF badge that keeps its red accent readable in both themes. */
export function DocumentIcon({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "grid size-9 shrink-0 place-items-center rounded-lg bg-red-500/10 text-red-500 dark:text-red-400",
        className,
      )}
    >
      <FileText className="size-4" />
    </span>
  );
}
