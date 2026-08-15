import { LoginForm } from "@/components/login-form";

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
    <main className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <LoginForm
        nextPath={safeNextPath(searchParams.next)}
        errorMessage={errorMessage}
      />
    </main>
  );
}
