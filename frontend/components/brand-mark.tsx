import Image from "next/image";

import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  compact?: boolean;
}

export function BrandMark({ className, compact = false }: BrandMarkProps) {
  return (
    <div className={cn("inline-flex items-center gap-2.5", className)}>
      <Image
        src="/brand/logo.png"
        alt="DocuMind"
        width={36}
        height={36}
        className="size-9 rounded-xl object-contain"
        priority
      />
      {!compact && (
        <span className="text-lg font-semibold tracking-tight">DocuMind</span>
      )}
    </div>
  );
}
