"use client";

import { Paperclip, Send, SlidersHorizontal, Square } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

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

export function ChatView() {
  const { messages, isStreaming, send, stop } = useChat();
  const { data: documents } = useDocuments();
  const { getInputProps, open: openUpload, isPending: uploading } = useUpload();
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState<string>(ALL_DOCUMENTS);
  const scrollRef = useRef<HTMLDivElement>(null);

  const readyDocuments = useMemo(
    () => documents?.filter((doc) => doc.status === "ready") ?? [],
    [documents],
  );

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    if (!question.trim() || isStreaming) {
      return;
    }
    void send(question, { documentId: scope === ALL_DOCUMENTS ? null : scope });
    setQuestion("");
  };

  return (
    <div className="flex h-full flex-col">
      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            No messages yet
          </h2>
          <p className="mt-3 max-w-md text-base text-muted-foreground sm:text-lg">
            Upload a PDF and ask a question to get a grounded, cited answer.
          </p>
        </div>
      ) : (
        <ScrollArea className="flex-1" viewportRef={scrollRef}>
          <div className="mx-auto max-w-3xl space-y-6 px-5 pb-6 pt-6 sm:px-8">
            {messages.map((message) => (
              <Message key={message.id} message={message} />
            ))}
          </div>
        </ScrollArea>
      )}

      <div className="px-5 pb-4 sm:px-8">
        <div className="mx-auto max-w-3xl">
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
                disabled={uploading}
                onClick={openUpload}
              >
                <Paperclip className="size-4" />
              </Button>

              <Select value={scope} onValueChange={setScope}>
                <SelectTrigger
                  className="h-8 w-auto gap-1.5 rounded-full border px-3 text-xs text-muted-foreground"
                  aria-label="Answer scope"
                >
                  <SlidersHorizontal className="size-3.5" />
                  <SelectValue />
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

              <div className="ml-auto">
                {isStreaming ? (
                  <Button
                    size="icon"
                    variant="outline"
                    className="size-9 rounded-xl"
                    onClick={stop}
                    aria-label="Stop"
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
                  >
                    <Send className="size-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            DocuMind answers each question independently (single-turn) and can make
            mistakes. Verify important information.
          </p>
        </div>
      </div>
    </div>
  );
}
