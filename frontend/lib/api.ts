import type { ApiErrorBody, DocumentResponse } from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = "error";
  let message = response.statusText || "Request failed";
  try {
    const body = (await response.json()) as Partial<ApiErrorBody>;
    if (body.error) {
      code = body.error.code;
      message = body.error.message;
    }
  } catch {
    // Non-JSON error body; keep the status-derived message.
  }
  return new ApiError(response.status, code, message);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), init);
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/healthz", { signal });
}

export function listDocuments(signal?: AbortSignal): Promise<DocumentResponse[]> {
  return request<DocumentResponse[]>("/documents", { signal });
}

export function getDocument(id: string, signal?: AbortSignal): Promise<DocumentResponse> {
  return request<DocumentResponse>(`/documents/${id}`, { signal });
}

export function uploadDocument(file: File): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<DocumentResponse>("/documents", {
    method: "POST",
    body: formData,
  });
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(`/documents/${id}`, { method: "DELETE" });
}
