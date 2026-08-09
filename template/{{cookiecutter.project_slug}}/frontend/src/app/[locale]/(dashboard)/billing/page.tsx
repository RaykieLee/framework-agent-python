"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  Download,
  ExternalLink,
  HardDrive,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { useLocale, useTranslations } from "next-intl";

import { StatCard } from "@/components/dashboard/stat-card";
import { LoadingState } from "@/components/states";
import { Alert, AlertDescription, AlertTitle, Badge, Button } from "@/components/ui";
import {
  useBilling,
  useCredits,
  useInvoices,
  useMembers,
  useOrganizations,
  useSubscription,
} from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn, formatBytes, formatCurrency, formatDate } from "@/lib/utils";

const STATUS_TONES: Record<string, string> = {
  trialing: "border-border text-muted-foreground",
  active: "border-border text-foreground",
  past_due: "border-yellow-500/40 text-yellow-600 dark:text-yellow-500",
  canceled: "border-destructive/40 text-destructive",
  unpaid: "border-destructive/40 text-destructive",
  incomplete: "border-border text-muted-foreground",
  incomplete_expired: "border-border text-muted-foreground",
  paused: "border-border text-muted-foreground",
};


export default function BillingOverviewPage() {
  const t = useTranslations("billing");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const { activeOrg, fetchOrgs } = useOrganizations();
  const { members } = useMembers(activeOrg?.id ?? "");
  const { subscription, isLoading: subLoading } = useSubscription();
  const { balance, isLoading: balanceLoading } = useCredits();
  const { invoices, isLoading: invoicesLoading } = useInvoices();
  const { openPortal, isLoading: portalLoading } = useBilling();
  const [storage, setStorage] = useState<{ total_bytes: number; limit_bytes: number } | null>(null);

  useEffect(() => {
    fetchOrgs();
  }, [fetchOrgs]);

  useEffect(() => {
    apiClient
      .get<{ total_bytes: number; limit_bytes: number }>("/billing/me/storage")
      .then(setStorage)
      .catch(() => setStorage(null));
  }, []);

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      toast.success(t("subscriptionUpdated"));
    }
  }, [searchParams]);

  const status = subscription?.status ?? "free";
  const statusLabel = ({
    trialing: t("statusTrial"), active: t("statusActive"), past_due: t("statusPastDue"),
    canceled: t("statusCanceled"), unpaid: t("statusUnpaid"), incomplete: t("statusIncomplete"),
    incomplete_expired: t("statusExpired"), paused: t("statusPaused"), free: t("statusFree"),
  } as Record<string, string>)[status] ?? t("statusFree");
  const statusTone = STATUS_TONES[status] ?? "border-border text-muted-foreground";
  const planName = subscription?.price?.plan?.display_name ?? t("statusFree");
  const seatsUsed = members?.length ?? 0;
  const seatsLimit = subscription?.seats_quantity ?? activeOrg?.seats_limit ?? null;
  const lowBalance =
    balance && balance.low_threshold > 0 && balance.balance < balance.low_threshold;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button onClick={() => openPortal()} disabled={portalLoading} variant="outline" size="sm">
          {portalLoading ? (
            t("opening")
          ) : (
            <>
              <ExternalLink className="h-3.5 w-3.5" />
              {t("manageStripe")}
            </>
          )}
        </Button>
      </div>

      {!balanceLoading && lowBalance && balance && (
        <Alert variant="warning">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{t("lowBalance")}</AlertTitle>
          <AlertDescription className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>
              {t("lowBalanceDesc", { balance: balance.balance.toLocaleString(), threshold: balance.low_threshold.toLocaleString() })}
            </span>
            <Link
              href={ROUTES.BILLING_CREDITS}
              className="text-foreground inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline"
            >
              {t("topUp")}
              <ArrowRight className="h-3 w-3" />
            </Link>
          </AlertDescription>
        </Alert>
      )}

      <section className="border-border bg-card rounded-xl border">
        <div className="grid gap-6 p-5 md:grid-cols-[1.4fr_1fr] md:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
                {t("currentPlan")}
              </span>
              <Badge variant="outline" className={cn("font-mono text-[10px] uppercase", statusTone)}>
                {statusLabel}
              </Badge>
            </div>
            <p className="text-foreground mt-2 text-2xl font-semibold tracking-tight">{planName}</p>
            {subscription ? (
              <p className="text-muted-foreground mt-1.5 text-sm">
                {t("renews", { date: formatDate(subscription.current_period_end, locale) })}
                {subscription.cancel_at_period_end && (
                  <span className="text-destructive ml-2 font-mono text-[11px] tracking-wider uppercase">
                    · {t("cancelsPeriodEnd")}
                  </span>
                )}
              </p>
            ) : !subLoading ? (
              <p className="text-muted-foreground mt-1.5 text-sm">
                {t("freePlanDesc")}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2 md:justify-end">
            {!subscription ? (
              <Button asChild>
                <Link href={ROUTES.PRICING}>
                  {t("seePlans")}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <Button asChild variant="outline">
                <Link href={ROUTES.BILLING_SUBSCRIPTION}>{t("managePlan")}</Link>
              </Button>
            )}
          </div>
        </div>
      </section>

      {balanceLoading ? (
        <LoadingState variant="stats" rows={3} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            label={t("creditsBalance")}
            value={(balance?.balance ?? 0).toLocaleString()}
            unit={t("creditsUnit")}
            icon={Sparkles}
          />
          {seatsLimit !== null && (
            <StatCard
              label={t("seats")}
              value={`${seatsUsed} / ${seatsLimit}`}
              icon={Users}
            />
          )}
          <StatCard
            label={t("storageUsed")}
            value={storage ? formatBytes(storage.total_bytes) : "—"}
            icon={HardDrive}
          />
        </div>
      )}

      <section className="border-border bg-card rounded-xl border">
        <div className="border-border flex items-center justify-between border-b px-5 py-4">
          <div>
            <h2 className="text-foreground text-sm font-semibold">{t("recentInvoices")}</h2>
            <p className="text-muted-foreground text-xs">
              {invoices.length === 0
                ? t("noInvoices")
                : t("invoiceCount", { shown: Math.min(5, invoices.length), total: invoices.length })}
            </p>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link href={ROUTES.BILLING_INVOICES}>{t("viewAll")}</Link>
          </Button>
        </div>

        {invoicesLoading ? (
          <div className="p-5">
            <LoadingState variant="skeleton-list" rows={3} />
          </div>
        ) : invoices.length === 0 ? (
          <div className="text-muted-foreground px-5 py-12 text-center text-sm">
            {t("invoiceEmptyDesc")}
          </div>
        ) : (
          <ul className="divide-border divide-y">
            {invoices.slice(0, 5).map((inv) => (
              <li key={inv.id} className="flex items-center gap-3 px-5 py-3.5">
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-medium">
                    {inv.number ?? t("invoiceNumber", { id: inv.id.slice(0, 8) })}
                  </p>
                  <p className="text-muted-foreground mt-0.5 text-xs">
                    {formatDate(inv.period_start, locale)} — {formatDate(inv.period_end, locale)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-foreground text-sm font-semibold tabular-nums">
                    {formatCurrency(inv.amount_due, inv.currency)}
                  </p>
                  <p className="text-muted-foreground mt-0.5 font-mono text-[10px] tracking-wider uppercase">
                    {inv.status}
                  </p>
                </div>
                {inv.invoice_pdf && (
                  <Button asChild variant="ghost" size="icon" className="shrink-0">
                    <a
                      href={inv.invoice_pdf}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={t("downloadPdf")}
                      aria-label={t("downloadPdf")}
                    >
                      <Download className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
