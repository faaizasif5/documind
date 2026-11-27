import type { DocumentResponse } from "@/lib/types";

/** Human label for a document that is still being ingested. */
export function processingLabel(document: DocumentResponse): string {
  if (document.total_chunks === null) return "Preparing…";
  return `Embedding ${document.processed_chunks} / ${document.total_chunks} chunks`;
}

/** 0–100 ingestion progress, or null while the total is still unknown. */
export function processingPercent(document: DocumentResponse): number | null {
  if (!document.total_chunks) return null;
  return Math.min(100, Math.round((document.processed_chunks / document.total_chunks) * 100));
}

export function failureReason(document: DocumentResponse): string {
  return document.error_message ?? "Processing failed.";
}
