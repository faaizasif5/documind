"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

interface LoginFormProps {
  nextPath: string;
  errorMessage?: string;
}

export function LoginForm({ nextPath, errorMessage }: LoginFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);

  const signInWithGoogle = async () => {
    setIsLoading(true);
    setClientError(null);

    const redirectTo = new URL("/auth/callback", window.location.origin);
    redirectTo.searchParams.set("next", nextPath);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: redirectTo.toString() },
    });

    if (error) {
      setClientError("Unable to start Google sign-in. Please try again.");
      setIsLoading(false);
    }
  };

  const message = clientError ?? errorMessage;

  return (
    <div className="w-full">
      <div className="mb-8">
        <p className="text-sm font-medium text-primary">Welcome back</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          Sign in to DocuMind
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          Continue with Google to access your private document workspace.
        </p>
      </div>

      {message && (
        <p
          role="alert"
          className="mb-5 rounded-xl border border-destructive/30 bg-destructive/10 p-3.5 text-sm text-destructive"
        >
          {message}
        </p>
      )}

      <Button
        variant="outline"
        className="h-11 w-full rounded-xl bg-background text-sm shadow-sm"
        onClick={signInWithGoogle}
        disabled={isLoading}
      >
        {!isLoading && (
          <svg viewBox="0 0 24 24" aria-hidden="true" className="size-4">
            <path
              fill="#4285F4"
              d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-2 3.02v2.54h3.24c1.9-1.74 2.98-4.31 2.98-7.41Z"
            />
            <path
              fill="#34A853"
              d="M12 22c2.7 0 4.97-.9 6.63-2.42l-3.24-2.54c-.9.6-2.05.96-3.39.96-2.61 0-4.82-1.76-5.61-4.13H3.04v2.62A10 10 0 0 0 12 22Z"
            />
            <path
              fill="#FBBC05"
              d="M6.39 13.87A6.02 6.02 0 0 1 6.07 12c0-.65.11-1.28.32-1.87V7.51H3.04A10 10 0 0 0 2 12c0 1.61.38 3.14 1.04 4.49l3.35-2.62Z"
            />
            <path
              fill="#EA4335"
              d="M12 6c1.47 0 2.79.5 3.83 1.5l2.87-2.87A9.64 9.64 0 0 0 12 2a10 10 0 0 0-8.96 5.51l3.35 2.62C7.18 7.76 9.39 6 12 6Z"
            />
          </svg>
        )}
        {isLoading ? "Redirecting to Google…" : "Continue with Google"}
      </Button>

      <p className="mt-6 text-center text-xs leading-5 text-muted-foreground">
        Your documents are isolated to your account and never shared with other
        users.
      </p>
    </div>
  );
}
