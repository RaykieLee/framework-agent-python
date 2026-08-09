"use client";

import { useTranslations } from "next-intl";

import { SectionCard } from "@/components/settings/settings-section";
import { ThemeToggle } from "@/components/theme";

export default function AppearanceSettingsPage() {
  const t = useTranslations("settings");
  return (
    <div className="space-y-6">
      <SectionCard title={t("theme")} description={t("themeDesc")}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-foreground text-sm font-medium">{t("colorScheme")}</p>
            <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
              {t("colorSchemeDesc")}
            </p>
          </div>
          <div className="shrink-0">
            <ThemeToggle variant="dropdown" />
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
