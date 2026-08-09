import { defaultLocale, type Locale } from "@/i18n";

/** Build a route that keeps the active locale when localePrefix is `as-needed`. */
export function localizedPath(locale: Locale, path: string): string {
  const match = path.match(/^([^?#]*)(.*)$/);
  const pathname = match?.[1] || "/";
  const suffix = match?.[2] || "";
  const normalized = pathname.startsWith("/") ? pathname : `/${pathname}`;

  if (locale === defaultLocale) return `${normalized}${suffix}`;
  if (normalized === "/") return `/${locale}${suffix}`;
  if (normalized === `/${locale}` || normalized.startsWith(`/${locale}/`)) {
    return `${normalized}${suffix}`;
  }
  return `/${locale}${normalized}${suffix}`;
}
