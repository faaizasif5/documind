"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import { streamChat } from "@/lib/sse";
import type { Source } from "@/lib/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  error: string | null;
  streaming: boolean;
  createdAt: number;
}

export interface SendOptions {
  documentId?: string | null;
  topK?: number;
}

function createId(): string {
  return globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const patchMessage = useCallback(
    (id: string, patch: (message: ChatMessage) => ChatMessage) => {
      setMessages((prev) =>
        prev.map((message) => (message.id === id ? patch(message) : message)),
      );
    },
    [],
  );

  const send = useCallback(
    async (question: string, options: SendOptions = {}) => {
      const trimmed = question.trim();
      if (!trimmed || isStreaming) {
        return;
      }

      const assistantId = createId();
      const now = Date.now();
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: "user",
          content: trimmed,
          sources: [],
          error: null,
          streaming: false,
          createdAt: now,
        },
        {
          id: assistantId,
          role: "assistant",
          content: "",
          sources: [],
          error: null,
          streaming: true,
          createdAt: now,
        },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      try {
        await streamChat(
          {
            question: trimmed,
            top_k: options.topK,
            document_id: options.documentId ?? null,
          },
          {
            onToken: (text) =>
              patchMessage(assistantId, (message) => ({
                ...message,
                content: message.content + text,
              })),
            onSources: (sources) =>
              patchMessage(assistantId, (message) => ({ ...message, sources })),
            onError: (errorMessage) =>
              patchMessage(assistantId, (message) => ({
                ...message,
                error: errorMessage,
              })),
          },
          controller.signal,
        );
        patchMessage(assistantId, (message) => ({ ...message, streaming: false }));
      } catch (error) {
        if (controller.signal.aborted) {
          patchMessage(assistantId, (message) => ({
            ...message,
            streaming: false,
            error: message.error ?? "Stopped.",
          }));
        } else {
          const text =
            error instanceof ApiError
              ? error.message
              : "Something went wrong while answering.";
          patchMessage(assistantId, (message) => ({
            ...message,
            streaming: false,
            error: text,
          }));
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, patchMessage],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, isStreaming, send, stop };
}
