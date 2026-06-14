import { ApiError, apiUrl } from "@/lib/api";
import type { ApiErrorBody, ChatRequest, Source } from "@/lib/types";

export interface ChatStreamHandlers {
  onToken: (text: string) => void;
  onSources: (sources: Source[]) => void;
  onError: (message: string) => void;
}

interface ParsedEvent {
  event: string;
  data: string;
}

function parseFrame(frame: string): ParsedEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return { event, data: dataLines.join("\n") };
}

function dispatch(parsed: ParsedEvent, handlers: ChatStreamHandlers): void {
  switch (parsed.event) {
    case "token": {
      const { text } = JSON.parse(parsed.data) as { text: string };
      handlers.onToken(text);
      break;
    }
    case "sources": {
      handlers.onSources(JSON.parse(parsed.data) as Source[]);
      break;
    }
    case "error": {
      const { message } = JSON.parse(parsed.data) as { message: string };
      handlers.onError(message);
      break;
    }
    default:
      break;
  }
}

/**
 * POSTs a chat request and consumes the Server-Sent Events response. The
 * browser's EventSource only supports GET, so we read the body stream directly.
 */
export async function streamChat(
  payload: ChatRequest,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(apiUrl("/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let code = "error";
    let message = "The assistant is unavailable right now";
    try {
      const body = (await response.json()) as Partial<ApiErrorBody>;
      if (body.error) {
        code = body.error.code;
        message = body.error.message;
      }
    } catch {
      // keep defaults
    }
    throw new ApiError(response.status, code, message);
  }

  if (!response.body) {
    throw new ApiError(502, "no_stream", "No response stream was returned");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    let separator = buffer.indexOf("\n\n");
    while (separator !== -1) {
      const frame = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);
      const parsed = parseFrame(frame);
      if (parsed) {
        dispatch(parsed, handlers);
      }
      separator = buffer.indexOf("\n\n");
    }
  }
}
