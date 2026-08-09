"use client";

import { useEffect, useMemo, useState } from "react";
import { CreditCard, MessageSquare, Sparkles, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

import { Button, Switch } from "@/components/ui";
import { SectionCard } from "@/components/settings/settings-section";

interface NotificationCategory {
  key: string;
  labelKey: string;
  descriptionKey: string;
  icon: LucideIcon;
  /** Default values for new users. */
  defaults: { email: boolean; inApp: boolean };
}

const CATEGORIES: NotificationCategory[] = [
  {
    key: "billing",
    labelKey: "catBilling",
    descriptionKey: "catBillingDesc",
    icon: CreditCard,
    defaults: { email: true, inApp: true },
  },
  {
    key: "members",
    labelKey: "catTeam",
    descriptionKey: "catTeamDesc",
    icon: Users,
    defaults: { email: true, inApp: true },
  },
  {
    key: "security",
    labelKey: "catSecurity",
    descriptionKey: "catSecurityDesc",
    icon: MessageSquare,
    defaults: { email: true, inApp: true },
  },
  {
    key: "product",
    labelKey: "catProduct",
    descriptionKey: "catProductDesc",
    icon: Sparkles,
    defaults: { email: false, inApp: true },
  },
];

const STORAGE_KEY = "settings.notifications.prefs";

type Prefs = Record<string, { email: boolean; inApp: boolean }>;

function defaultPrefs(): Prefs {
  return Object.fromEntries(
    CATEGORIES.map((c) => [c.key, { email: c.defaults.email, inApp: c.defaults.inApp }]),
  );
}

function loadPrefs(): Prefs {
  if (typeof window === "undefined") return defaultPrefs();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultPrefs();
    return { ...defaultPrefs(), ...(JSON.parse(raw) as Prefs) };
  } catch {
    return defaultPrefs();
  }
}

function savePrefs(prefs: Prefs) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export default function NotificationsSettingsPage() {
  const t = useTranslations("settings");
  const [prefs, setPrefs] = useState<Prefs>(defaultPrefs);
  const [dirty, setDirty] = useState(false);
  const initialPrefs = useMemo(loadPrefs, []);

  useEffect(() => {
    setPrefs(initialPrefs);
  }, [initialPrefs]);

  const toggle = (key: string, channel: "email" | "inApp") => {
    setPrefs((prev) => ({
      ...prev,
      [key]: {
        email: prev[key]?.email ?? true,
        inApp: prev[key]?.inApp ?? true,
        [channel]: !(prev[key]?.[channel] ?? true),
      },
    }));
    setDirty(true);
  };

  const handleSave = () => {
    savePrefs(prefs);
    toast.success(t("preferencesSaved"));
    setDirty(false);
  };

  const handleReset = () => {
    setPrefs(defaultPrefs());
    setDirty(true);
  };

  return (
    <div className="space-y-6">
      <SectionCard
        title={t("notificationsTitle")}
        description={t("notificationsDesc")}
        action={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleReset}>
              {t("resetDefaults")}
            </Button>
            <Button onClick={handleSave} disabled={!dirty} size="sm">
              {t("saveChanges")}
            </Button>
          </div>
        }
      >
        <div className="border-border overflow-hidden rounded-xl border">
          <div className="border-border bg-muted grid grid-cols-[1fr_70px_70px] items-center gap-2 border-b px-5 py-3 sm:grid-cols-[1.5fr_90px_90px]">
            <span className="text-muted-foreground text-[11px] font-medium tracking-wide uppercase">
              {t("category")}
            </span>
            <span className="text-muted-foreground text-center text-[11px] font-medium tracking-wide uppercase">
              {t("email")}
            </span>
            <span className="text-muted-foreground text-center text-[11px] font-medium tracking-wide uppercase">
              {t("inApp")}
            </span>
          </div>
          <ul className="divide-border divide-y">
            {CATEGORIES.map((c) => {
              const p = prefs[c.key] ?? c.defaults;
              return (
                <li
                  key={c.key}
                  className="hover:bg-accent grid grid-cols-[1fr_70px_70px] items-center gap-2 px-5 py-4 transition-colors sm:grid-cols-[1.5fr_90px_90px]"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="bg-muted text-muted-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                      <c.icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-foreground text-sm font-medium">{t(c.labelKey)}</p>
                      <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
                        {t(c.descriptionKey)}
                      </p>
                    </div>
                  </div>
                  <div className="flex justify-center">
                    <Switch
                      checked={p.email}
                      onCheckedChange={() => toggle(c.key, "email")}
                      aria-label={t("emailFor", { category: t(c.labelKey) })}
                    />
                  </div>
                  <div className="flex justify-center">
                    <Switch
                      checked={p.inApp}
                      onCheckedChange={() => toggle(c.key, "inApp")}
                      aria-label={t("inAppFor", { category: t(c.labelKey) })}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
        <p className="text-muted-foreground mt-4 text-xs leading-relaxed">
          {t("preferencesLocal")}
        </p>
      </SectionCard>
    </div>
  );
}
