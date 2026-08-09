"use client";

import { useTranslations } from "next-intl";

import { PaymentMethodsPanel } from "@/components/billing";

export default function PaymentMethodsPage() {
  const t = useTranslations("billing");
  return (
    <div className="space-y-4">
      <p className="text-muted-foreground text-sm">
        {t("paymentIntro")}
      </p>
      <PaymentMethodsPanel />
    </div>
  );
}
