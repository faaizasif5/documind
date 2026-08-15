"use client";

import {
  ArrowDown,
  Loader2,
  Paperclip,
  Plus,
  Send,
  SlidersHorizontal,
  Square,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ChatEmptyState } from "@/components/chat-empty-state";
import { Message } from "@/components/message";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@/hooks/use-chat";
import { useDocuments } from "@/hooks/use-documents";
import { useUpload } from "@/hooks/use-upload";

const ALL_DOCUMENTS = "all";
/** Distance from the bottom that still counts as "following" the stream. */
const NEAR_BOTTOM_PX = 120;

export function ChatView() {
  const { messages, isStreaming, send, stop, clear } = useChat();
  const { data: documents } = useDocuments();
  const {
    getInputProps,
    open: openUpload,
    isPending: uploading,
    progress,
  } = useUpload();
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState<string>(ALL_DOCUMENTS);
  const [following, setFollowing] = useState(true);
  const viewportRef = useRef<HTMLDivElement>(null);

  const readyDocuments = useMemo(
    () => documents?.filter((doc) => doc.status === "ready") ?? [],
    [documents],
  );

  // Drop a scope that points at a deleted document so requests stay valid.
  useEffect(() => {
    if (scope !== ALL_DOCUMENTS && !readyDocuments.some((doc) => doc.id === scope)) {
      setScope(ALL_DOCUMENTS);
    }
  }, [readyDocuments, scope]);

  const scrollToBottom = useCallback((smooth = false) => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }
    viewport.scrollTo({
      top: viewport.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  }, []);

  // Track whether the user is still near the bottom before auto-scrolling, so
  // scrolling up to re-read an answer isn't undone by the next token.
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }
    const onScroll = () => {
      const distance =
        viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
      setFollowing(distance < NEAR_BOTTOM_PX);
    };
    viewport.addEventListener("scroll", onScroll, { passive: true });
    return () => viewport.removeEventListener("scroll", onScroll);
  }, [messages.length]);

  useEffect(() => {
    if (following) {
      scrollToBottom();
    }
  }, [messages, following, scrollToBottom]);

  const ask = (text: string) => {
    if (!text.trim() || isStreaming) {
      return;
    }
    setFollowing(true);
    void send(text, { documentId: scope === ALL_DOCUMENTS ? null : scope });
  };

  const submit = () => {
    if (!question.trim() || isStreaming) {
      return;
    }
    ask(question);
    setQuestion("");
  };

  const hasReadyDocuments = readyDocuments.length > 0;

  return (
    <div className="relative isolate flex h-full flex-col">
      {/* Same ambient glow the marketing hero uses, so both surfaces read alike. */}
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-80 bg-[radial-gradient(ellipse_at_top,hsl(var(--primary)/0.10),transparent_65%)]" />

      {messages.length === 0 ? (
        <ChatEmptyState onPickPrompt={ask} />
      ) : (
        <>
          <div className="mx-auto flex w-full max-w-4xl shrink-0 justify-end px-5 pt-3 sm:px-8">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 text-xs text-muted-foreground"
              onClick={clear}
            >
              <Plus className="size-3.5" />
              New chat
            </Button>
          </div>

          <div className="relative min-h-0 flex-1">
            <ScrollArea className="h-full" viewportRef={viewportRef}>
              <div className="mx-auto max-w-4xl space-y-8 px-5 pb-6 pt-3 sm:px-8">
                {messages.map((message) => (
                  <Message key={message.id} message={message} />
                ))}
              </div>
            </ScrollArea>

            {!following && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setFollowing(true);
                  scrollToBottom(true);
                }}
                className="absolute bottom-4 left-1/2 h-8 -translate-x-1/2 gap-1.5 rounded-full border text-xs shadow-md"
              >
                <ArrowDown className="size-3.5" />
                Jump to latest
              </Button>
            )}
          </div>
        </>
      )}

      <div className="shrink-0 px-5 pb-4 sm:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="rounded-2xl border bg-card p-2 shadow-sm focus-within:ring-1 focus-within:ring-ring">
            <Textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit();
                }
              }}
              placeholder="Ask a question about your documents…"
              rows={1}
              className="max-h-40 min-h-[2.5rem] resize-none border-0 bg-transparent px-2 shadow-none focus-visible:ring-0"
            />
            <div className="flex items-center gap-2 px-1 pt-1">
              <input {...getInputProps()} />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-8 text-muted-foreground"
                aria-label="Upload PDF"
                title="Upload PDF"
                disabled={uploading}
                onClick={openUpload}
              >
                {uploading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Paperclip className="size-4" />
                )}
              </Button>

              <Select
                value={scope}
                onValueChange={setScope}
                disabled={!hasReadyDocuments}
              >
                <SelectTrigger
                  className="h-8 w-auto max-w-[13rem] gap-1.5 rounded-full border px-3 text-xs text-muted-foreground"
                  aria-label="Answer scope"
                  title={
                    hasReadyDocuments
                      ? "Limit answers to one document"
                      : "Upload a document to choose a scope"
                  }
                >
                  <SlidersHorizontal className="size-3.5 shrink-0" />
                  <span className="truncate">
                    <SelectValue
                      placeholder={
                        hasReadyDocuments ? "All documents" : "No documents ready"
                      }
                    />
                  </span>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_DOCUMENTS}>All documents</SelectItem>
                  {readyDocuments.map((doc) => (
                    <SelectItem key={doc.id} value={doc.id}>
                      {doc.filename}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {uploading && (
                <span className="hidden text-xs text-muted-foreground sm:inline">
                  {progress >= 100 ? "Processing…" : `Uploading ${progress}%`}
                </span>
              )}

              <div className="ml-auto">
                {isStreaming ? (
                  <Button
                    size="icon"
                    variant="outline"
                    className="size-9 rounded-xl"
                    onClick={stop}
                    aria-label="Stop generating"
                    title="Stop generating"
                  >
                    <Square className="size-4" />
                  </Button>
                ) : (
                  <Button
                    size="icon"
                    className="size-9 rounded-xl"
                    onClick={submit}
                    disabled={!question.trim()}
                    aria-label="Send"
                    title="Send"
                  >
                    <Send className="size-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            <span className="hidden sm:inline">
              Enter to send · Shift+Enter for a new line ·{" "}
            </span>
            Each question is answered independently and can contain mistakes.
          </p>
        </div>
      </div>
    </div>
  );
}
