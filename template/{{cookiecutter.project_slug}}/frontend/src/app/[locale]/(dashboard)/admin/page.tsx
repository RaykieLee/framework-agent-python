"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  CreditCard,
  MessageSquare,
  RefreshCw,
  Star,
  UserPlus,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
import { LoadingState } from "@/components/states";
import { Button } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { formatCurrency, timeAgo } from "@/lib/utils";
import { localizedPath } from "@/lib/locale-path";
import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n";

interface AdminStats {
  total_users?: number;
  active_users_24h?: number;
  total_conversations?: number;
  total_messages?: number;
  credits_charged_30d?: number;
  mrr_cents?: number;
}

interface RecentEvent {
  id: string;
  type: "user_signup" | "conversation_created" | "subscription_renewed" | "rating_low";
  title: string;
  description: string;
  timestamp: string;
}

const EVENT_ICON: Record<RecentEvent["type"], LucideIcon> = {
  user_signup: UserPlus,
  conversation_created: MessageSquare,
  subscription_renewed: CreditCard,
  rating_low: Star,
};


export default function AdminOverviewPage() {
  const locale = useLocale() as Locale;
  const t = useTranslations("admin");
  const statsQuery = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: async (): Promise<AdminStats> => {
      const data = await apiClient.get<AdminStats>("/admin/stats").catch(() => null);
      if (data) return data;
      const [usersResp, convsResp] = await Promise.allSettled([
        apiClient.get<{ total: number }>("/admin/users?limit=1"),
        apiClient.get<{ total: number }>("/admin/conversations?limit=1"),
      ]);
      return {
        total_users: usersResp.status === "fulfilled" ? usersResp.value.total : undefined,
        total_conversations: convsResp.status === "fulfilled" ? convsResp.value.total : undefined,
      };
    },
  });

  const eventsQuery = useQuery({
    queryKey: ["admin", "events"],
    queryFn: async (): Promise<RecentEvent[]> => {
      const events = await apiClient.get<{ items: RecentEvent[] }>("/admin/events").catch(() => null);
      if (events) return events.items.slice(0, 8);
      const convs = await apiClient
        .get<{
          items: Array<{ id: string; user_email?: string; title?: string; created_at: string }>;
        }>("/admin/conversations?limit=8")
        .catch(() => ({ items: [] }));
      return convs.items.map((c) => ({
        id: c.id,
        type: "conversation_created" as const,
        title: c.title || t("newConversation"),
        description: c.user_email ? t("byUser", { email: c.user_email }) : "",
        timestamp: c.created_at,
      }));
    },
  });

  const stats = statsQuery.data;
  const events = eventsQuery.data;
  const refreshing = statsQuery.isFetching || eventsQuery.isFetching;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            statsQuery.refetch();
            eventsQuery.refetch();
          }}
        >
          <RefreshCw className={refreshing ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} />
          {t("refresh")}
        </Button>
      </div>

      {statsQuery.isLoading ? (
        <LoadingState variant="stats" rows={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("totalUsers")} value={(stats?.total_users ?? 0).toLocaleString()} icon={Users} />
          <StatCard
            label={t("active24h")}
            value={(stats?.active_users_24h ?? 0).toLocaleString()}
            icon={Activity}
          />
          <StatCard
            label={t("conversations")}
            value={(stats?.total_conversations ?? 0).toLocaleString()}
            icon={MessageSquare}
          />
          <StatCard
            label="MRR"
            value={
              typeof stats?.mrr_cents === "number"
                ? formatCurrency(stats.mrr_cents)
                : "—"
            }
            icon={CreditCard}
          />
        </div>
      )}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <QuickLink href={localizedPath(locale, ROUTES.ADMIN_USERS)} icon={Users} title={t("manageUsers")} description={t("manageUsersDesc")} />
        <QuickLink
          href={localizedPath(locale, ROUTES.ADMIN_CONVERSATIONS)}
          icon={MessageSquare}
          title={t("browseChats")}
          description={t("browseChatsDesc")}
        />
        <QuickLink
          href={localizedPath(locale, ROUTES.ADMIN_STRIPE_EVENTS)}
          icon={CreditCard}
          title={t("stripeEvents")}
          description={t("stripeEventsDesc")}
        />
        <QuickLink href={localizedPath(locale, ROUTES.ADMIN_SYSTEM)} icon={Activity} title={t("systemHealth")} description={t("systemHealthDesc")} />
        <QuickLink href={localizedPath(locale, ROUTES.ADMIN_RATINGS)} icon={Star} title={t("responseRatings")} description={t("responseRatingsDesc")} />
      </section>

      <section className="border-border bg-card rounded-xl border">
        <div className="border-border border-b px-5 py-4">
          <h2 className="text-foreground text-sm font-semibold">{t("recentActivity")}</h2>
          <p className="text-muted-foreground text-xs">{t("recentActivityDesc")}</p>
        </div>
        {events === undefined ? (
          <div className="p-5">
            <LoadingState variant="skeleton-list" rows={5} />
          </div>
        ) : events.length === 0 ? (
          <div className="text-muted-foreground px-5 py-12 text-center text-sm">{t("noRecentEvents")}</div>
        ) : (
          <ul className="divide-border divide-y">
            {events.map((e) => {
              const Icon = EVENT_ICON[e.type] ?? MessageSquare;
              return (
                <li key={e.id} className="flex items-center gap-3 px-5 py-3.5">
                  <span className="bg-muted text-muted-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-foreground truncate text-sm font-medium">{e.title}</p>
                    <p className="text-muted-foreground truncate text-xs">
                      {e.description}
                      {e.description && " · "}
                      {timeAgo(e.timestamp)}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function QuickLink({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="border-border hover:border-foreground/30 hover:bg-accent bg-card group flex items-center gap-3 rounded-xl border p-4 transition-colors"
    >
      <span className="bg-muted text-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-foreground text-sm font-semibold">{title}</p>
        <p className="text-muted-foreground truncate text-xs">{description}</p>
      </div>
      <ArrowUpRight className="text-muted-foreground h-4 w-4" />
    </Link>
  );
}
