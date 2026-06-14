export type DocumentStatus = "processing" | "ready" | "failed";

export interface DocumentResponse {
  id: string;
  filename: string;
  file_size: number;
  page_count: number;
  status: DocumentStatus;
  created_at: string;
}

export interface Source {
  document_id: string;
  filename: string;
  page_number: number;
}

export interface ChatRequest {
  question: string;
  top_k?: number;
  document_id?: string | null;
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
