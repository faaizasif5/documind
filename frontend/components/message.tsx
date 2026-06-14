"use client";

import { AlertCircle, Check, Copy, Sparkles, User } from "lucide-react";
import { useState } from "react";

import { CitationChips } from "@/components/citation-chips";
import { SourcesCard } from "@/components/sources-card";
import type { ChatMessage } from "@/hooks/use-chat";

function formatTime(ms: number): string {
  return new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      type="button"
      aria-label="Copy answer"
      className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      onClick={() => {
        void navigator.clipboard?.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
    </button>
  );
}

export function Message({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3">
        <div className="flex max-w-[80%] flex-col items-end">
          <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
            <p className="whitespace-pre-wrap break-words leading-relaxed">
              {message.content}
            </p>
          </div>
          <span className="mt-1 px-1 text-[11px] text-muted-foreground">
            {formatTime(message.createdAt)}
          </span>
        </div>
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <User className="size-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 text-white">
        <Sparkles className="size-4" />
      </div>
      <div className="min-w-0 max-w-[85%] space-y-2">
        <div className="rounded-2xl rounded-tl-sm border bg-card px-4 py-3 text-sm shadow-sm">
          {message.content && (
            <p className="whitespace-pre-wrap break-words leading-relaxed">
              {message.content}
            </p>
          )}

          {message.streaming && !message.content && (
            <span className="inline-flex gap-1 py-1" aria-label="Thinking">
              <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground" />
              <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:150ms]" />
              <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:300ms]" />
            </span>
          )}

          {message.error && (
            <p className="flex items-center gap-1.5 text-sm text-destructive">
              <AlertCircle className="size-4 shrink-0" />
              {message.error}
            </p>
          )}

          <CitationChips sources={message.sources} />

          {!message.streaming && message.content && (
            <div className="mt-2 flex items-center gap-1 border-t pt-2">
              <span className="text-[11px] text-muted-foreground">
                {formatTime(message.createdAt)}
              </span>
              <div className="ml-auto">
                <CopyButton text={message.content} />
              </div>
            </div>
          )}
        </div>

        <SourcesCard sources={message.sources} />
      </div>
    </div>
  );
}
