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
    <div className="w-full max-w-sm rounded-xl border bg-card p-6 shadow-sm">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in to DocuMind</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Continue with Google to access your documents.
        </p>
      </div>

      {message && (
        <p
          role="alert"
          className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {message}
        </p>
      )}

      <Button className="w-full" onClick={signInWithGoogle} disabled={isLoading}>
        {isLoading ? "Redirecting…" : "Continue with Google"}
      </Button>
    </div>
  );
}
