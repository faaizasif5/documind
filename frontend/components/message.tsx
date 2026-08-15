"use client";

import { AlertCircle, Check, Copy, RotateCcw, Sparkles } from "lucide-react";
import { useState } from "react";

import { MarkdownAnswer } from "@/components/markdown-answer";
import { SourcesList, sourceAnchorId } from "@/components/sources-list";
import { useChat, type ChatMessage } from "@/hooks/use-chat";

function formatTime(ms: number): string {
  return new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const actionClass =
  "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      type="button"
      className={actionClass}
      onClick={() => {
        void navigator.clipboard?.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function ThinkingDots() {
  return (
    <span className="flex gap-1 py-2">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          style={{ animationDelay: `${delay}ms` }}
          className="size-1.5 rounded-full bg-muted-foreground/70 motion-safe:animate-bounce"
        />
      ))}
    </span>
  );
}

export function Message({ message }: { message: ChatMessage }) {
  const { regenerate, isStreaming } = useChat();
  const [highlighted, setHighlighted] = useState<number | null>(null);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm text-primary-foreground">
          <p className="whitespace-pre-wrap break-words leading-relaxed">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  const showActions = !message.streaming && message.content.length > 0;

  const focusSource = (sourceNumber: number) => {
    setHighlighted(sourceNumber);
    document
      .getElementById(sourceAnchorId(message.id, sourceNumber))
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  };

  return (
    <div className="group/message">
      <div className="mb-2 flex items-center gap-2">
        <span className="grid size-6 place-items-center rounded-full bg-primary/10 text-primary">
          <Sparkles className="size-3.5" />
        </span>
        <span className="text-xs font-medium">DocuMind</span>
        <span className="text-xs text-muted-foreground">
          {formatTime(message.createdAt)}
        </span>
      </div>

      <div
        aria-live="polite"
        aria-busy={message.streaming}
        className="min-w-0 break-words"
      >
        {message.content ? (
          <MarkdownAnswer
            content={message.content}
            sourceNumbers={message.sources.map((source) => source.number)}
            onCitationClick={focusSource}
          />
        ) : (
          message.streaming && <ThinkingDots />
        )}
      </div>

      {message.error && (
        <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          {message.error}
        </p>
      )}

      <SourcesList
        sources={message.sources}
        messageId={message.id}
        highlighted={highlighted}
      />

      {showActions && (
        <div className="mt-2 flex items-center gap-1">
          <CopyButton text={message.content} />
          <button
            type="button"
            className={actionClass}
            disabled={isStreaming || !message.prompt}
            onClick={() => void regenerate(message.id)}
          >
            <RotateCcw className="size-3.5" />
            Regenerate
          </button>
        </div>
      )}
    </div>
  );
}
