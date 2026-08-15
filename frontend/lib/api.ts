import { AuthRequiredError, buildApiHeaders, redirectToLogin } from "@/lib/auth-headers";
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

function parseErrorBody(
  raw: string,
): { code: string; message: string } | null {
  try {
    const body = JSON.parse(raw) as Partial<ApiErrorBody>;
    return body.error ? { code: body.error.code, message: body.error.message } : null;
  } catch {
    return null;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  const fallback = response.statusText || "Request failed";
  const parsed = parseErrorBody(await response.text());
  return new ApiError(
    response.status,
    parsed?.code ?? "error",
    parsed?.message ?? fallback,
  );
}

interface RequestOptions extends RequestInit {
  /** When true (default), attach Bearer token. Health checks set false. */
  requireAuth?: boolean;
}

async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
  const { requireAuth = true, headers: initHeaders, ...rest } = init;

  let headers: Headers;
  try {
    headers = await buildApiHeaders(initHeaders, { requireAuth });
  } catch (error) {
    if (error instanceof AuthRequiredError) {
      throw new ApiError(401, "unauthorized", "Authentication required");
    }
    throw error;
  }

  const response = await fetch(apiUrl(path), { ...rest, headers });

  if (response.status === 401 && requireAuth) {
    await redirectToLogin();
    throw new ApiError(401, "unauthorized", "Authentication required");
  }

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
  return request<HealthResponse>("/healthz", { signal, requireAuth: false });
}

export function listDocuments(signal?: AbortSignal): Promise<DocumentResponse[]> {
  return request<DocumentResponse[]>("/documents", { signal });
}

export function getDocument(id: string, signal?: AbortSignal): Promise<DocumentResponse> {
  return request<DocumentResponse>(`/documents/${id}`, { signal });
}

/**
 * Uploads via XHR rather than fetch because only XHR reports request upload
 * progress, which the UI needs for the transfer bar.
 */
export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<DocumentResponse> {
  let headers: Headers;
  try {
    headers = await buildApiHeaders();
  } catch (error) {
    if (error instanceof AuthRequiredError) {
      throw new ApiError(401, "unauthorized", "Authentication required");
    }
    throw error;
  }

  const formData = new FormData();
  formData.append("file", file);

  return new Promise<DocumentResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl("/documents"));
    headers.forEach((value, key) => xhr.setRequestHeader(key, value));

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        onProgress?.(Math.round((event.loaded / event.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status === 401) {
        void redirectToLogin();
        reject(new ApiError(401, "unauthorized", "Authentication required"));
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        const parsed = parseErrorBody(xhr.responseText);
        reject(
          new ApiError(
            xhr.status,
            parsed?.code ?? "error",
            parsed?.message ?? "Upload failed",
          ),
        );
        return;
      }
      try {
        resolve(JSON.parse(xhr.responseText) as DocumentResponse);
      } catch {
        reject(new ApiError(502, "invalid_response", "Malformed upload response"));
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError(0, "network_error", "Upload failed — check your connection")),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError(0, "aborted", "Upload cancelled")),
    );

    xhr.send(formData);
  });
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(`/documents/${id}`, { method: "DELETE" });
}
