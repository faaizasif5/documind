"use client";

import { useCallback } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { toast } from "sonner";

import { useUploadDocument } from "@/hooks/use-documents";
import { ApiError } from "@/lib/api";

const MAX_BYTES = 10 * 1024 * 1024;

export function useUpload({ enableDrag = false }: { enableDrag?: boolean } = {}) {
  const upload = useUploadDocument();

  const onDrop = useCallback(
    (accepted: File[], rejections: FileRejection[]) => {
      if (rejections.length > 0) {
        toast.error(rejections[0].errors[0]?.message ?? "File rejected");
        return;
      }
      const file = accepted[0];
      if (!file) {
        return;
      }
      upload.mutate(file, {
        onSuccess: (doc) => toast.success(`Uploaded "${doc.filename}" — processing…`),
        onError: (error) =>
          toast.error(error instanceof ApiError ? error.message : "Upload failed"),
      });
    },
    [upload],
  );

  const dropzone = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxSize: MAX_BYTES,
    multiple: false,
    noDrag: !enableDrag,
    disabled: upload.isPending,
  });

  return { ...dropzone, isPending: upload.isPending, maxBytes: MAX_BYTES };
}
