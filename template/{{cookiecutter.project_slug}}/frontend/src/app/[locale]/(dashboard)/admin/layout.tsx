"use client";

import type { ReactNode } from "react";
import { Activity, CreditCard, LayoutDashboard, MessageSquare, Star, Users } from "lucide-react";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";
import { useTranslations } from "next-intl";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const t = useTranslations("admin");
  const tabs: PageTab[] = [
    { label: t("overview"), href: ROUTES.ADMIN, icon: LayoutDashboard, exact: true },
    { label: t("users"), href: ROUTES.ADMIN_USERS, icon: Users },
    { label: t("conversations"), href: ROUTES.ADMIN_CONVERSATIONS, icon: MessageSquare },
    { label: t("ratings"), href: ROUTES.ADMIN_RATINGS, icon: Star },
    { label: t("stripeEvents"), href: ROUTES.ADMIN_STRIPE_EVENTS, icon: CreditCard },
    { label: t("system"), href: ROUTES.ADMIN_SYSTEM, icon: Activity },
  ];
  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("workspaceAdministration")}
        description={t("workspaceAdministrationDesc")}
      />
      <PageTabs tabs={tabs} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
