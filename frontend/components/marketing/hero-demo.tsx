"use client";

import { ArrowUp, FileText, Loader2, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { BrandMark } from "@/components/brand-mark";
import {
  DEMO_DOCUMENTS,
  DEMO_QUERIES,
  DEMO_RETRIEVAL_DELAY_MS,
  DEMO_TYPING_INTERVAL_MS,
} from "@/lib/marketing-content";
import { cn } from "@/lib/utils";

type Phase = "retrieving" | "streaming" | "done";

export function HeroDemo() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [typed, setTyped] = useState("");
  const [phase, setPhase] = useState<Phase>("retrieving");
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  const runQuery = useCallback(
    (index: number) => {
      clearTimers();
      const { answer } = DEMO_QUERIES[index];
      setActiveIndex(index);

      const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;

      if (reducedMotion) {
        setTyped(answer);
        setPhase("done");
        return;
      }

      setTyped("");
      setPhase("retrieving");

      timers.current.push(
        setTimeout(() => {
          setPhase("streaming");
          for (let i = 1; i <= answer.length; i += 1) {
            timers.current.push(
              setTimeout(() => {
                setTyped(answer.slice(0, i));
                if (i === answer.length) {
                  setPhase("done");
                }
              }, i * DEMO_TYPING_INTERVAL_MS),
            );
          }
        }, DEMO_RETRIEVAL_DELAY_MS),
      );
    },
    [clearTimers],
  );

  useEffect(() => {
    runQuery(0);
    return clearTimers;
  }, [runQuery, clearTimers]);

  const active = DEMO_QUERIES[activeIndex];
  const isBusy = phase !== "done";

  return (
    <div className="relative">
      <div className="pointer-events-none absolute -inset-x-6 -inset-y-10 -z-10 rounded-[3rem] bg-primary/10 blur-3xl motion-safe:animate-gradient-drift" />

      <div className="overflow-hidden rounded-2xl border bg-card shadow-2xl shadow-primary/10 ring-1 ring-black/[0.02]">
        <div className="flex h-11 items-center gap-2 border-b bg-muted/40 px-4">
          <span className="size-2.5 rounded-full bg-red-400/70" />
          <span className="size-2.5 rounded-full bg-amber-400/70" />
          <span className="size-2.5 rounded-full bg-emerald-400/70" />
          <div className="mx-auto rounded-md border bg-background px-10 py-1 text-[10px] text-muted-foreground sm:px-20">
            documind.app
          </div>
        </div>

        <div className="grid md:grid-cols-[14.5rem_1fr]">
          <aside className="hidden border-r bg-muted/20 p-5 md:block">
            <BrandMark />
            <p className="mb-3 mt-7 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Documents
            </p>
            <ul className="space-y-1.5">
              {DEMO_DOCUMENTS.map((name) => {
                const isCited = active.citations.some(
                  (citation) => citation.document === name,
                );
                return (
                  <li
                    key={name}
                    className={cn(
                      "flex items-center gap-2 rounded-lg p-2.5 text-xs transition-all duration-300",
                      isCited
                        ? "border bg-background font-medium shadow-sm"
                        : "text-muted-foreground",
                    )}
                  >
                    <FileText
                      className={cn("size-4", isCited && "text-primary")}
                    />
                    <span className="truncate">{name}</span>
                  </li>
                );
              })}
            </ul>

            <div className="mt-6 rounded-xl border bg-background/60 p-3">
              <p className="flex items-center gap-1.5 text-[11px] font-medium text-primary">
                <Sparkles className="size-3" />
                Indexed &amp; ready
              </p>
              <p className="mt-1 text-[11px] leading-4 text-muted-foreground">
                Chunks embedded for semantic retrieval.
              </p>
            </div>
          </aside>

          <div className="flex min-h-[24rem] flex-col p-5 sm:p-7">
            <div className="flex flex-wrap gap-2">
              {DEMO_QUERIES.map((query, index) => (
                <button
                  key={query.question}
                  type="button"
                  onClick={() => runQuery(index)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-left text-[11px] transition-colors sm:text-xs",
                    index === activeIndex
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted",
                  )}
                >
                  {query.question}
                </button>
              ))}
            </div>

            <div className="mt-6 flex flex-1 flex-col justify-end gap-4">
              <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm text-primary-foreground shadow-sm">
                {active.question}
              </div>

              <div className="max-w-[92%] rounded-2xl rounded-bl-md border bg-muted/30 p-4 shadow-sm">
                {phase === "retrieving" ? (
                  <p className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-3.5 animate-spin" />
                    Searching your documents…
                  </p>
                ) : (
                  <p className="text-sm leading-6">
                    {typed}
                    {phase === "streaming" && (
                      <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 bg-primary align-middle motion-safe:animate-blink" />
                    )}
                  </p>
                )}

                {phase === "done" && (
                  <div className="mt-3 flex flex-wrap gap-2 motion-safe:animate-fade-up">
                    {active.citations.map((citation, index) => (
                      <span
                        key={`${citation.document}-${citation.page}`}
                        className="inline-flex items-center gap-1.5 rounded-full border bg-background px-2.5 py-1 text-[11px] text-muted-foreground"
                      >
                        <span className="font-medium text-primary">
                          {index + 1}
                        </span>
                        {citation.document} · p.{citation.page}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6 flex items-center gap-3 rounded-xl border bg-background p-3 shadow-sm">
              <span className="truncate text-sm text-muted-foreground">
                Ask a question about your documents…
              </span>
              <button
                type="button"
                aria-label="Replay demo answer"
                onClick={() => runQuery(activeIndex)}
                disabled={isBusy}
                className="ml-auto grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground transition-opacity disabled:opacity-50"
              >
                {isBusy ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <ArrowUp className="size-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
