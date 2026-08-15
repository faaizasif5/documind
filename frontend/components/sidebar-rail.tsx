"use client";

import { ChevronsRight, Plus } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { Button } from "@/components/ui/button";
import { authUserLabel, useAuthUser } from "@/hooks/use-auth-user";
import { useUpload } from "@/hooks/use-upload";

export function SidebarRail({ onExpand }: { onExpand: () => void }) {
  const { getInputProps, open, isPending } = useUpload();
  const user = useAuthUser();

  return (
    <div className="flex h-full w-16 flex-col items-center gap-1 bg-muted/25 py-4">
      <BrandMark compact />

      <Button
        variant="ghost"
        size="icon"
        className="mt-1 size-9 text-muted-foreground"
        aria-label="Expand sidebar"
        title="Expand sidebar"
        onClick={onExpand}
      >
        <ChevronsRight className="size-4" />
      </Button>

      <input {...getInputProps()} />
      <Button
        size="icon"
        className="mt-3 size-10 rounded-lg"
        aria-label="Upload PDF"
        title="Upload PDF"
        disabled={isPending}
        onClick={open}
      >
        <Plus className="size-5" />
      </Button>

      {user && (
        <div
          title={authUserLabel(user)}
          className="mt-auto grid size-9 place-items-center rounded-full bg-primary/10 text-sm font-semibold uppercase text-primary"
        >
          {authUserLabel(user).slice(0, 1)}
        </div>
      )}
    </div>
  );
}
