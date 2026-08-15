import { AppShell } from "@/components/app-shell";
import { MarketingLanding } from "@/components/marketing-landing";
import { createClient } from "@/lib/supabase/server";

export default async function Home() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return user ? <AppShell /> : <MarketingLanding />;
}
