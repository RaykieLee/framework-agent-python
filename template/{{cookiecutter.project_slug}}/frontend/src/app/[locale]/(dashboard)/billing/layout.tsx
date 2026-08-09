"use client";

import type { ReactNode } from "react";
import { BarChart3, CreditCard, FileText, LayoutDashboard, Sparkles, Wallet } from "lucide-react";
import { useTranslations } from "next-intl";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";

export default function BillingLayout({ children }: { children: ReactNode }) {
  const t = useTranslations("billing");
  const tabs: PageTab[] = [
    { label: t("tabOverview"), href: ROUTES.BILLING, icon: LayoutDashboard, exact: true },
    { label: t("tabUsage"), href: ROUTES.BILLING_USAGE, icon: BarChart3 },
    { label: t("tabCredits"), href: ROUTES.BILLING_CREDITS, icon: Sparkles },
    { label: t("tabInvoices"), href: ROUTES.BILLING_INVOICES, icon: FileText },
    { label: t("tabPaymentMethods"), href: ROUTES.BILLING_PAYMENT_METHODS, icon: Wallet },
    { label: t("tabSubscription"), href: ROUTES.BILLING_SUBSCRIPTION, icon: CreditCard },
  ];
  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("pageTitle")}
        description={t("pageDescription")}
      />
      <PageTabs tabs={tabs} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
