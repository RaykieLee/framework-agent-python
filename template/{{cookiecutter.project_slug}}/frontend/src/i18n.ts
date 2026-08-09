import { getRequestConfig } from "next-intl/server";
export const locales = ["en", "pl", "zh"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;

  if (!locale || !locales.includes(locale as Locale)) {
    locale = defaultLocale;
  }

  const messages = (await import(`../messages/${locale}.json`)).default;

  return {
    locale,
    messages: {
      ...messages,
      // Admin copy extends the shared navigation vocabulary while keeping
      // page-specific translations in the admin namespace.
      admin: { ...messages.nav, ...messages.admin },
    },
  };
});

export function getLocaleLabel(locale: Locale): string {
  const labels: Record<Locale, string> = {
    en: "English",
    pl: "Polski",
    zh: "中文",
  };
  return labels[locale];
}

export function getLocaleFlag(locale: Locale): string {
  const flags: Record<Locale, string> = {
    en: "🇬🇧",
    pl: "🇵🇱",
    zh: "🇨🇳",
  };
  return flags[locale];
}
