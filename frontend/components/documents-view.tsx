"use client";

import { DocumentList } from "@/components/document-list";
import { UploadDropzone } from "@/components/upload-dropzone";

export function DocumentsView() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-5 py-6 sm:px-8">
      <UploadDropzone />
      <DocumentList />
    </div>
  );
}
