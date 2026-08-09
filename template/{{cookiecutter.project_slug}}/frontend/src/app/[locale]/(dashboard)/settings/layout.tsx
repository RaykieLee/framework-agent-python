"use client";

import type { ReactNode } from "react";
import { Bell, Palette, {% if cookiecutter.enable_mcp_client %}Plug, {% endif %}Shield, Slash, UserCircle } from "lucide-react";
import { useTranslations } from "next-intl";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const t = useTranslations("settings");
  const tabs: PageTab[] = [
    { label: t("tabProfile"), href: ROUTES.SETTINGS_PROFILE, icon: UserCircle },
    { label: t("tabAccount"), href: ROUTES.SETTINGS_ACCOUNT, icon: Shield },
    { label: t("tabCommands"), href: ROUTES.SETTINGS_SLASH_COMMANDS, icon: Slash },
{%- if cookiecutter.enable_mcp_client %}
    { label: t("tabIntegrations"), href: ROUTES.SETTINGS_INTEGRATIONS, icon: Plug },
{%- endif %}
    { label: t("tabNotifications"), href: ROUTES.SETTINGS_NOTIFICATIONS, icon: Bell },
    { label: t("tabAppearance"), href: ROUTES.SETTINGS_APPEARANCE, icon: Palette },
  ];
  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        description={t("description")}
      />
      <PageTabs tabs={tabs} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
