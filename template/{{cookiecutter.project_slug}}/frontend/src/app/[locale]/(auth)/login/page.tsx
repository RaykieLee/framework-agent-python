import type { Metadata } from "next";

import { LoginForm } from "@/components/auth";
import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";
import { getTranslations } from "next-intl/server";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "auth" });
  return pageMetadata({
    title: t("loginPageTitle"),
    description: t("loginPageDescription"),
    path: "/login",
    locale,
    noindex: true,
  });
}

export default function LoginPage() {
  return <LoginForm />;
}
