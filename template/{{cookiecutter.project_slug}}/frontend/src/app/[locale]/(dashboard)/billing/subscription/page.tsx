"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Check } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

import { SubscriptionPanel } from "@/components/billing";
import { LoadingState } from "@/components/states";
import { Badge, Button } from "@/components/ui";
import { useBilling, usePlans } from "@/hooks";
import { cn, formatCurrency } from "@/lib/utils";

export default function SubscriptionPage() {
  const t = useTranslations("billing");
  const searchParams = useSearchParams();
  const { plans, isLoading: plansLoading } = usePlans();
  const { startCheckout, isLoading: checkoutLoading } = useBilling();

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      toast.success(t("subscriptionUpdated"));
    }
  }, [searchParams]);

  return (
    <div className="space-y-6">
      <SubscriptionPanel />

      <section className="space-y-3">
        <div>
          <h2 className="text-foreground text-sm font-semibold">{t("switchPlan")}</h2>
          <p className="text-muted-foreground text-xs">
            {t("switchPlanDesc")}
          </p>
        </div>

        {plansLoading ? (
          <LoadingState variant="skeleton-cards" rows={3} />
        ) : plans.length === 0 ? (
          <p className="text-muted-foreground text-sm">{t("noPlans")}</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan) => {
              const activePrices = plan.prices.filter((p) => p.is_active);
              return (
                <article
                  key={plan.id}
                  className={cn(
                    "bg-card flex flex-col rounded-xl border p-5 transition-colors",
                    plan.is_active
                      ? "border-foreground/30"
                      : "border-border hover:border-foreground/30",
                  )}
                >
                  <header className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-foreground text-base font-semibold">
                        {plan.display_name}
                      </h3>
                      {plan.is_active && (
                        <Badge variant="outline" className="text-[10px] uppercase">
                          {t("current")}
                        </Badge>
                      )}
                    </div>
                    {plan.description && (
                      <p className="text-muted-foreground text-xs leading-relaxed">
                        {plan.description}
                      </p>
                    )}
                  </header>

                  <ul className="my-5 space-y-1.5 text-sm">
                    {activePrices.map((price) => (
                      <li key={price.id} className="flex items-baseline justify-between gap-2">
                        <span className="text-muted-foreground">{price.interval === "month" ? t("month") : t("year")}</span>
                        <span className="text-foreground font-mono tabular-nums">
                          {formatCurrency(price.amount_cents, price.currency)}
                        </span>
                      </li>
                    ))}
                    {plan.monthly_credits_base > 0 && (
                      <li className="text-muted-foreground flex items-center gap-1.5 pt-1 text-xs">
                        <Check className="h-3.5 w-3.5" />
                        {t("creditsPerMonth", { count: plan.monthly_credits_base.toLocaleString() })}
                      </li>
                    )}
                  </ul>

                  <div className="mt-auto space-y-2">
                    {activePrices.map((price) => (
                      <Button
                        key={price.id}
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={checkoutLoading}
                        onClick={() =>
                          startCheckout({
                            price_id: price.id,
                            success_url: window.location.href + "?success=1",
                            cancel_url: window.location.href,
                          })
                        }
                        className="w-full"
                      >
                        {t("chooseInterval", { interval: price.interval === "month" ? t("month") : t("year") })}
                      </Button>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
