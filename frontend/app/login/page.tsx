import { ArrowLeft, CheckCircle2, Quote } from "lucide-react";
import Link from "next/link";

import { BrandMark } from "@/components/brand-mark";
import { HealthBadge } from "@/components/health-badge";
import { LoginForm } from "@/components/login-form";
import { ThemeToggle } from "@/components/theme-toggle";

interface LoginPageProps {
  searchParams: {
    next?: string;
    error?: string;
  };
}

function safeNextPath(value: string | undefined): string {
  return value?.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export default function LoginPage({ searchParams }: LoginPageProps) {
  const errorMessage =
    searchParams.error === "auth_callback_failed"
      ? "Google sign-in could not be completed. Please try again."
      : undefined;

  return (
    <main className="grid min-h-screen bg-background lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-foreground p-12 text-background lg:flex lg:flex-col">
        <div className="pointer-events-none absolute -right-36 -top-36 size-[32rem] rounded-full bg-primary/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-48 -left-32 size-[30rem] rounded-full bg-primary/20 blur-3xl" />

        <BrandMark className="relative z-10" />

        <div className="relative z-10 my-auto max-w-xl">
          <p className="text-sm font-medium text-background/60">Your knowledge, unlocked</p>
          <h2 className="mt-4 text-5xl font-semibold leading-[1.08] tracking-[-0.035em]">
            Turn long documents into clear, cited answers.
          </h2>
          <p className="mt-6 max-w-lg text-base leading-7 text-background/65">
            Search by meaning, ask questions naturally, and verify every answer
            against its original page.
          </p>

          <div className="mt-10 grid gap-3 text-sm text-background/75">
            <span className="flex items-center gap-3">
              <CheckCircle2 className="size-4 text-primary" />
              Grounded answers from your uploaded PDFs
            </span>
            <span className="flex items-center gap-3">
              <CheckCircle2 className="size-4 text-primary" />
              Page-level citations on every relevant source
            </span>
            <span className="flex items-center gap-3">
              <CheckCircle2 className="size-4 text-primary" />
              Private workspace isolated to your account
            </span>
          </div>

          <blockquote className="mt-12 rounded-2xl border border-background/10 bg-background/5 p-5">
            <Quote className="size-5 text-primary" />
            <p className="mt-3 text-sm leading-6 text-background/75">
              “Instead of searching page by page, ask the question and jump straight
              to the evidence.”
            </p>
          </blockquote>
        </div>

        <p className="relative z-10 text-xs text-background/40">
          Secure Google authentication · Per-user document isolation
        </p>
      </section>

      <section className="relative flex min-h-screen items-center justify-center px-5 py-12 sm:px-10">
        <div className="absolute left-5 top-5 flex items-center gap-2 lg:hidden">
          <BrandMark />
        </div>
        <div className="absolute right-4 top-4 flex items-center gap-2">
          <HealthBadge />
          <ThemeToggle />
        </div>

        <div className="w-full max-w-md">
          <Link
            href="/"
            className="mb-8 inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Back to home
          </Link>
          <div className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
            <LoginForm
              nextPath={safeNextPath(searchParams.next)}
              errorMessage={errorMessage}
            />
          </div>
        </div>
      </section>
    </main>
  );
}
