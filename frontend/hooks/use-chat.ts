"use client";

import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "@/lib/api";
import { streamChat } from "@/lib/sse";
import type { Source } from "@/lib/types";

export interface ChatPrompt {
  question: string;
  documentId: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  error: string | null;
  streaming: boolean;
  createdAt: number;
  /** Present on assistant messages so the answer can be regenerated. */
  prompt?: ChatPrompt;
}

interface ChatContextValue {
  messages: ChatMessage[];
  isStreaming: boolean;
  send: (question: string, prompt?: Partial<ChatPrompt>) => Promise<void>;
  regenerate: (assistantId: string) => Promise<void>;
  stop: () => void;
  clear: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

function createId(): string {
  return globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);
}

/** Holds the transcript above the view switcher so navigation doesn't discard it. */
export function ChatProvider({ children }: { children: ReactNode }) {
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

  const runStream = useCallback(
    async (assistantId: string, prompt: ChatPrompt) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      try {
        await streamChat(
          {
            question: prompt.question,
            document_id: prompt.documentId,
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
        const text = controller.signal.aborted
          ? "Stopped."
          : error instanceof ApiError
            ? error.message
            : "Something went wrong while answering.";
        patchMessage(assistantId, (message) => ({
          ...message,
          streaming: false,
          error: message.error ?? text,
        }));
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [patchMessage],
  );

  const send = useCallback(
    async (question: string, options: Partial<ChatPrompt> = {}) => {
      const trimmed = question.trim();
      if (!trimmed || isStreaming) {
        return;
      }

      const prompt: ChatPrompt = {
        question: trimmed,
        documentId: options.documentId ?? null,
      };
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
          prompt,
        },
      ]);

      await runStream(assistantId, prompt);
    },
    [isStreaming, runStream],
  );

  const regenerate = useCallback(
    async (assistantId: string) => {
      if (isStreaming) {
        return;
      }
      const target = messages.find((message) => message.id === assistantId);
      if (!target?.prompt) {
        return;
      }

      patchMessage(assistantId, (message) => ({
        ...message,
        content: "",
        sources: [],
        error: null,
        streaming: true,
        createdAt: Date.now(),
      }));

      await runStream(assistantId, target.prompt);
    },
    [isStreaming, messages, patchMessage, runStream],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
  }, []);

  const value = useMemo<ChatContextValue>(
    () => ({ messages, isStreaming, send, regenerate, stop, clear }),
    [messages, isStreaming, send, regenerate, stop, clear],
  );

  return createElement(ChatContext.Provider, { value }, children);
}

export function useChat(): ChatContextValue {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
}
