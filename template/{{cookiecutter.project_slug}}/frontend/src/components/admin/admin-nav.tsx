"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  Activity,
  CreditCard,
  LayoutDashboard,
  MessageSquare,
  Star,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { localizedPath } from "@/lib/locale-path";
import type { Locale } from "@/i18n";

interface NavItem {
  labelKey: string;
  href: string;
  icon: LucideIcon;
  description?: string;
}

const ITEMS: NavItem[] = [
  { labelKey: "overview", href: ROUTES.ADMIN, icon: LayoutDashboard },
  { labelKey: "users", href: ROUTES.ADMIN_USERS, icon: Users },
  { labelKey: "conversations", href: ROUTES.ADMIN_CONVERSATIONS, icon: MessageSquare },
  { labelKey: "ratings", href: ROUTES.ADMIN_RATINGS, icon: Star },
  { labelKey: "stripeEvents", href: ROUTES.ADMIN_STRIPE_EVENTS, icon: CreditCard },
  { labelKey: "systemHealth", href: ROUTES.ADMIN_SYSTEM, icon: Activity },
];

export function AdminNav() {
  const pathname = usePathname();
  const locale = useLocale() as Locale;
  const t = useTranslations("nav");
  const stripped = pathname.replace(/^\/[a-z]{2}/, "");

  return (
    <>      <nav className="hidden lg:block">
        <p className="text-foreground/45 mb-3 px-3 font-mono text-[10px] tracking-wider uppercase">
          {t("admin")}
        </p>
        <ul className="space-y-0.5">
          {ITEMS.map((item) => {
            const active =
              item.href === "/admin"
                ? stripped === "/admin"
                : stripped === item.href || stripped.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={localizedPath(locale, item.href)}
                  className={cn(
                    "group flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-foreground/10 text-foreground"
                      : "text-foreground/65 hover:bg-foreground/5 hover:text-foreground",
                  )}
                >
                  <item.icon
                    className={cn(
                      "h-4 w-4 shrink-0",
                      active ? "text-foreground" : "text-foreground/40 group-hover:text-foreground",
                    )}
                  />
                  <span className="font-medium">{t(item.labelKey)}</span>
                  {active && (
                    <span aria-hidden className="bg-brand ml-auto h-1.5 w-1.5 rounded-full" />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>      <nav className="-mx-3 flex scrollbar-thin gap-1.5 overflow-x-auto px-3 pb-2 lg:hidden">
        {ITEMS.map((item) => {
          const active =
            item.href === "/admin"
              ? stripped === "/admin"
              : stripped === item.href || stripped.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={localizedPath(locale, item.href)}
              className={cn(
                "border-foreground/15 inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                active
                  ? "bg-foreground text-background border-foreground"
                  : "text-foreground/65 hover:text-foreground hover:border-foreground/40",
              )}
            >
              <item.icon className="h-3.5 w-3.5" />
              {t(item.labelKey)}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
