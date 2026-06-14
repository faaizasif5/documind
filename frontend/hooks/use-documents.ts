"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  deleteDocument,
  listDocuments,
  uploadDocument,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { DocumentResponse } from "@/lib/types";

const POLL_INTERVAL_MS = 2_000;

export function useDocuments() {
  return useQuery({
    queryKey: queryKeys.documents,
    queryFn: ({ signal }) => listDocuments(signal),
    // Keep polling while any document is still being processed.
    refetchInterval: (query) => {
      const documents = query.state.data;
      const hasProcessing = documents?.some((doc) => doc.status === "processing");
      return hasProcessing ? POLL_INTERVAL_MS : false;
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: (created: DocumentResponse) => {
      queryClient.setQueryData<DocumentResponse[]>(queryKeys.documents, (prev) =>
        prev ? [created, ...prev] : [created],
      );
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: (_data, id) => {
      queryClient.setQueryData<DocumentResponse[]>(queryKeys.documents, (prev) =>
        prev?.filter((doc) => doc.id !== id),
      );
    },
  });
}
