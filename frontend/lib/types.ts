export type DocumentStatus = "processing" | "ready" | "failed";

export interface DocumentResponse {
  id: string;
  filename: string;
  file_size: number;
  page_count: number;
  status: DocumentStatus;
  /** Chunks embedded and stored so far. */
  processed_chunks: number;
  /** Null until the PDF has been chunked. */
  total_chunks: number | null;
  /** User-safe failure reason when status is "failed". */
  error_message: string | null;
  created_at: string;
}

export interface Source {
  /** Matches the inline [Source N] marker in the answer text. */
  number: number;
  document_id: string;
  filename: string;
  page_number: number;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  question: string;
  top_k?: number;
  document_id?: string | null;
  history?: ChatTurn[];
}

export interface FieldError {
  field: string;
  message: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: FieldError[] | null;
  };
}
