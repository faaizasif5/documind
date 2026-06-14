"use client";

import { Loader2, UploadCloud } from "lucide-react";

import { useUpload } from "@/hooks/use-upload";
import { cn } from "@/lib/utils";

export function UploadDropzone() {
  const { getRootProps, getInputProps, isDragActive, isPending } = useUpload({
    enableDrag: true,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-6 py-10 text-center transition-colors",
        isDragActive ? "border-primary bg-accent" : "border-border hover:bg-accent/50",
        isPending && "pointer-events-none opacity-60",
      )}
    >
      <input {...getInputProps()} />
      <div className="flex size-11 items-center justify-center rounded-full bg-accent text-primary">
        {isPending ? (
          <Loader2 className="size-5 animate-spin" />
        ) : (
          <UploadCloud className="size-5" />
        )}
      </div>
      <p className="mt-3 text-sm font-medium">
        {isDragActive ? "Drop the PDF here" : "Drag a PDF here, or click to browse"}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">PDF only · up to 10 MB</p>
    </div>
  );
}
