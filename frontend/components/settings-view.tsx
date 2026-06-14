"use client";

import { Info } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useHealth } from "@/hooks/use-health";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b py-2.5 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

export function SettingsView() {
  const { data, isError } = useHealth();
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-5 py-6 sm:px-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Backend</CardTitle>
          <CardDescription>Live status of the DocuMind API.</CardDescription>
        </CardHeader>
        <CardContent>
          <Row label="API base URL" value={apiBase} />
          <Row label="Service" value={data?.service ?? "—"} />
          <Row label="Status" value={isError ? "Offline" : (data?.status ?? "Checking…")} />
        </CardContent>
      </Card>

      <div className="flex items-start gap-2 rounded-xl border bg-accent/40 p-4 text-sm text-muted-foreground">
        <Info className="mt-0.5 size-4 shrink-0" />
        <p>
          DocuMind runs in single-user mode with no authentication. Chat is single-turn:
          each question is answered independently with no conversation memory.
        </p>
      </div>
    </div>
  );
}
