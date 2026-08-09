{% raw %}import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n";
import { ROUTES } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Check your email",
    description: "We sent you a sign-in link.",
    path: "/magic-link-sent",
    locale,
    noindex: true,
  });
}

interface PageProps {
  searchParams: Promise<{ email?: string }>;
}

export default async function MagicLinkSentPage({ searchParams }: PageProps) {
  const { email } = await searchParams;
  const t = await getTranslations("auth.magicLink");

  return (
    <div className="space-y-8 text-center">
      <div
        className="bg-brand/15 mx-auto flex h-16 w-16 items-center justify-center rounded-full"
        style={{ boxShadow: "0 0 40px oklch(from var(--color-brand) l c h / 0.4)" }}
      >
        <Mail className="text-foreground h-7 w-7" />
      </div>

      <div className="space-y-2">
        <span className="eyebrow text-foreground/55">{t("eyebrow")}</span>
        <h1 className="text-display-md text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          {t("heading")} <em>{t("headingAccent")}</em>
        </h1>
        <p className="text-foreground/70 text-sm">
          {t("sent")}
          {email ? (
            <>
              {" "}{t("to")} <span className="text-foreground font-medium">{email}</span>
            </>
          ) : null}
          。{t("expires")}
        </p>
      </div>

      <div className="border-foreground/10 bg-foreground/[0.03] rounded-2xl border px-5 py-4 text-left">
        <p className="text-foreground/70 text-xs leading-relaxed">
          {t("notSeeingIt")} {" "}
          <Link
            href={ROUTES.LOGIN}
            className="text-foreground hover:text-foreground/80 font-medium underline-offset-4 hover:underline"
          >
            {t("tryAgain")}
          </Link>
          .
        </p>
      </div>

      <Link
        href={ROUTES.LOGIN}
        className="text-foreground/55 hover:text-foreground inline-flex items-center gap-2 text-sm font-medium"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("backToSignIn")}
      </Link>
    </div>
  );
}
{% endraw %}
