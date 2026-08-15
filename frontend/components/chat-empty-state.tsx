"use client";

import { ArrowRight, FileUp, Loader2, MessageSquareText } from "lucide-react";

import { UploadProgress } from "@/components/upload-progress";
import { useDocuments } from "@/hooks/use-documents";
import { useUpload } from "@/hooks/use-upload";
import { buildStarterPrompts } from "@/lib/chat-prompts";
import { cn } from "@/lib/utils";

interface ChatEmptyStateProps {
  onPickPrompt: (prompt: string) => void;
}

export function ChatEmptyState({ onPickPrompt }: ChatEmptyStateProps) {
  const { data: documents, isLoading } = useDocuments();
  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isPending,
    progress,
    maxBytes,
  } = useUpload({ enableDrag: true });

  const readyFilenames =
    documents?.filter((doc) => doc.status === "ready").map((doc) => doc.filename) ?? [];
  const processingCount =
    documents?.filter((doc) => doc.status === "processing").length ?? 0;
  const prompts = buildStarterPrompts(readyFilenames);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 size-4 animate-spin" />
        Loading your library…
      </div>
    );
  }

  const hasDocuments = (documents?.length ?? 0) > 0;

  return (
    <div className="flex flex-1 items-center justify-center px-5 py-10 sm:px-8">
      <div className="w-full max-w-3xl text-center">
        <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-primary/10 text-primary">
          <MessageSquareText className="size-6" />
        </span>
        <h2 className="mt-5 text-2xl font-semibold tracking-tight">
          {hasDocuments ? "Ask your first question" : "Upload a PDF to get started"}
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          {hasDocuments
            ? "Answers come only from your documents, with the page they came from."
            : "Drop in a handbook, contract, or policy and ask questions about it in plain English."}
        </p>

        {prompts.length > 0 && (
          <div className="mt-7 space-y-2 text-left">
            {prompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => onPickPrompt(prompt)}
                className="group flex w-full items-center gap-3 rounded-xl border bg-card p-3.5 text-sm transition-colors hover:border-primary/30 hover:bg-accent/40"
              >
                <span className="min-w-0 flex-1 truncate">{prompt}</span>
                <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
              </button>
            ))}
          </div>
        )}

        {prompts.length === 0 && processingCount > 0 && (
          <p className="mt-7 inline-flex items-center gap-2 rounded-xl border bg-card px-4 py-3 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            {processingCount === 1
              ? "Your document is being indexed…"
              : `${processingCount} documents are being indexed…`}
          </p>
        )}

        {!hasDocuments && (
          <div
            {...getRootProps()}
            className={cn(
              "mt-7 cursor-pointer rounded-2xl border-2 border-dashed p-8 transition-colors",
              isDragActive
                ? "border-primary bg-primary/5"
                : "hover:border-primary/40 hover:bg-muted/40",
              isPending && "pointer-events-none opacity-70",
            )}
          >
            <input {...getInputProps()} />
            <FileUp className="mx-auto size-7 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium">
              {isDragActive ? "Drop your PDF here" : "Drag a PDF here, or click to browse"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              PDF only · up to {Math.round(maxBytes / (1024 * 1024))} MB
            </p>
            {isPending && <UploadProgress percent={progress} className="mt-5" />}
          </div>
        )}
      </div>
    </div>
  );
}
