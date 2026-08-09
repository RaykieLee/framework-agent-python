"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { useAuthStore } from "@/stores";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import type { User } from "@/types";
import { Spinner } from "@/components/ui";
import { localizedPath } from "@/lib/locale-path";
import type { Locale } from "@/i18n";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const locale = useLocale() as Locale;
  const { setUser } = useAuthStore();
  // Zustand persists the user for a fast first paint, but the actual session
  // lives in HTTP-only cookies. Always revalidate before mounting children so
  // stale local state cannot trigger a burst of 401 requests.
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const verify = async () => {
      try {
        const user = await apiClient.get<User>("/auth/me");
        setUser(user);
      } catch {
        router.replace(localizedPath(locale, ROUTES.LOGIN));
      } finally {
        setChecking(false);
      }
    };

    verify();
  }, [locale, router, setUser]);

  if (checking) {
    return (
      <div className="flex h-screen items-center justify-center" role="status" aria-live="polite">
        <Spinner className="text-muted-foreground h-6 w-6" />
        <span className="sr-only">Checking authentication...</span>
      </div>
    );
  }

  return <>{children}</>;
}
