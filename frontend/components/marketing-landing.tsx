import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { HeroDemo } from "@/components/marketing/hero-demo";
import { Reveal } from "@/components/marketing/reveal";
import { SpotlightCard } from "@/components/marketing/spotlight-card";
import { WorkflowSteps } from "@/components/marketing/workflow-steps";
import { ThemeToggle } from "@/components/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import {
  MARKETING_FAQS,
  MARKETING_FEATURES,
  MARKETING_STATS,
  NAV_LINKS,
  PRIVACY_TAGLINE,
  PRIVACY_TRUST_POINTS,
} from "@/lib/marketing-content";
import { cn } from "@/lib/utils";

const navLinkClass =
  "relative py-1 transition-colors after:absolute after:inset-x-0 after:-bottom-0.5 after:h-0.5 after:origin-left after:scale-x-0 after:bg-primary after:transition-transform hover:text-foreground hover:after:scale-x-100";

export function MarketingLanding() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-xl">
        <nav className="mx-auto flex h-16 max-w-7xl items-center px-5 sm:px-8">
          <BrandMark />
          <div className="ml-auto flex items-center gap-1 sm:gap-3">
            <div className="mr-3 hidden items-center gap-6 text-sm text-muted-foreground md:flex">
              {NAV_LINKS.map(({ href, label }) => (
                <Link key={href} href={href} className={navLinkClass}>
                  {label}
                </Link>
              ))}
            </div>
            <ThemeToggle />
            <Link
              href="/login"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              Sign in
            </Link>
          </div>
        </nav>
      </header>

      <main>
        <section className="relative isolate overflow-hidden px-5 pb-20 pt-16 sm:px-8 sm:pb-28 sm:pt-24">
          <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[42rem] bg-[radial-gradient(ellipse_at_top,hsl(var(--primary)/0.14),transparent_62%)]" />
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(to_right,hsl(var(--border))_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border))_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] opacity-[0.35] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]" />

          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-3xl text-center">
              <Reveal>
                <Link
                  href="/login"
                  className="group mb-6 inline-flex items-center gap-2 rounded-full border bg-background/80 px-3.5 py-1.5 text-xs font-medium text-muted-foreground shadow-sm transition-colors hover:border-primary/30 hover:text-foreground"
                >
                  <Sparkles className="size-3.5 text-primary" />
                  Your PDFs, now conversational
                  <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Reveal>
              <Reveal delay={80}>
                <h1 className="text-balance text-4xl font-semibold tracking-[-0.035em] sm:text-6xl lg:text-7xl">
                  Answers from your documents,{" "}
                  <span className="bg-gradient-to-br from-primary to-primary/60 bg-clip-text text-transparent">
                    with proof.
                  </span>
                </h1>
              </Reveal>
              <Reveal delay={160}>
                <p className="mx-auto mt-6 max-w-2xl text-pretty text-base leading-7 text-muted-foreground sm:text-xl sm:leading-8">
                  Upload PDFs, ask questions in plain English, and get focused
                  answers grounded in the source—with page-level citations.
                </p>
              </Reveal>
              <Reveal delay={240}>
                <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                  <Link
                    href="/login"
                    className={cn(
                      buttonVariants({ size: "lg" }),
                      "group h-11 rounded-xl px-6 shadow-lg shadow-primary/20 transition-transform hover:-translate-y-0.5",
                    )}
                  >
                    Start asking
                    <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                  </Link>
                  <Link
                    href="#how-it-works"
                    className={cn(
                      buttonVariants({ variant: "outline", size: "lg" }),
                      "h-11 rounded-xl px-6",
                    )}
                  >
                    See how it works
                  </Link>
                </div>
              </Reveal>
              <Reveal delay={300}>
                <p className="mt-4 text-xs text-muted-foreground">
                  Free to try · Google sign-in · No credit card
                </p>
                <p className="mx-auto mt-2 max-w-lg text-xs leading-5 text-muted-foreground/90">
                  {PRIVACY_TAGLINE}
                </p>
              </Reveal>
            </div>

            <Reveal delay={200} className="mx-auto mt-16 max-w-5xl sm:mt-20">
              <HeroDemo />
            </Reveal>

            <Reveal
              delay={120}
              className="mx-auto mt-16 grid max-w-4xl gap-6 border-t pt-10 sm:grid-cols-3"
            >
              {MARKETING_STATS.map(({ value, label }) => (
                <div key={label} className="text-center">
                  <p className="text-2xl font-semibold tracking-tight sm:text-3xl">
                    {value}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">{label}</p>
                </div>
              ))}
            </Reveal>
          </div>
        </section>

        <section
          id="features"
          className="border-y bg-muted/25 px-5 py-20 sm:px-8 sm:py-28"
        >
          <div className="mx-auto max-w-7xl">
            <Reveal className="max-w-2xl">
              <p className="text-sm font-medium text-primary">Built for trust</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                Less searching. More understanding.
              </h2>
              <p className="mt-4 text-muted-foreground">
                DocuMind combines semantic retrieval with grounded AI responses so
                every answer stays connected to your content.
              </p>
            </Reveal>
            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {MARKETING_FEATURES.map(
                ({ icon: Icon, title, description }, index) => (
                  <Reveal key={title} delay={index * 70}>
                    <SpotlightCard
                      icon={<Icon className="size-5" />}
                      title={title}
                      description={description}
                      className="h-full"
                    />
                  </Reveal>
                ),
              )}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="px-5 py-20 sm:px-8 sm:py-28">
          <div className="mx-auto max-w-7xl">
            <Reveal className="mx-auto max-w-2xl text-center">
              <p className="text-sm font-medium text-primary">Simple by design</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                From PDF to answer in three steps
              </h2>
              <p className="mt-4 text-muted-foreground">
                Follow along—each step shows what DocuMind is doing behind the
                scenes.
              </p>
            </Reveal>
            <Reveal delay={100} className="mt-14">
              <WorkflowSteps />
            </Reveal>
          </div>
        </section>

        <section
          id="faq"
          className="border-t bg-muted/25 px-5 py-20 sm:px-8 sm:py-28"
        >
          <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[22rem_1fr] lg:gap-16">
            <Reveal>
              <p className="text-sm font-medium text-primary">Good to know</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                Questions, answered.
              </h2>
              <p className="mt-4 text-muted-foreground">
                The short version of how DocuMind handles your documents.
              </p>
            </Reveal>
            <Reveal delay={100} className="divide-y rounded-2xl border bg-card">
              {MARKETING_FAQS.map(({ question, answer }) => (
                <details key={question} className="group px-5 py-4 sm:px-6">
                  <summary className="flex cursor-pointer list-none items-center gap-4 font-medium [&::-webkit-details-marker]:hidden">
                    {question}
                    <ChevronDown className="ml-auto size-4 shrink-0 text-muted-foreground transition-transform duration-300 group-open:rotate-180" />
                  </summary>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground motion-safe:animate-fade-up">
                    {answer}
                  </p>
                </details>
              ))}
            </Reveal>
          </div>
        </section>

        <section className="px-5 py-20 sm:px-8 sm:py-24">
          <Reveal className="mx-auto max-w-7xl">
            <div className="relative isolate overflow-hidden rounded-3xl border bg-card px-6 py-14 sm:px-12">
              <div className="pointer-events-none absolute -right-16 -top-24 -z-10 size-72 rounded-full bg-primary/20 blur-3xl motion-safe:animate-gradient-drift" />
              <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_bottom_left,hsl(var(--primary)/0.08),transparent_55%)]" />
              <div className="grid items-center gap-8 md:grid-cols-[1fr_auto]">
                <div>
                  <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
                    <ShieldCheck className="size-4 text-primary" />
                    Private by default
                  </div>
                  <h2 className="text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                    Ask from your PDFs — without keeping the files.
                  </h2>
                  <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
                    {PRIVACY_TAGLINE}
                  </p>
                  <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
                    {PRIVACY_TRUST_POINTS.map((point) => (
                      <span key={point} className="inline-flex items-center gap-2">
                        <CheckCircle2 className="size-4 shrink-0 text-primary" />
                        {point}
                      </span>
                    ))}
                  </div>
                </div>
                <Link
                  href="/login"
                  className={cn(
                    buttonVariants({ size: "lg" }),
                    "group h-11 rounded-xl shadow-lg shadow-primary/20 transition-transform hover:-translate-y-0.5",
                  )}
                >
                  Try DocuMind
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="border-t px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <BrandMark />
          <p>Grounded answers from the documents that matter.</p>
        </div>
      </footer>
    </div>
  );
}
