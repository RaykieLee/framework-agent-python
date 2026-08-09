"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  Download,
  ExternalLink,
  MessageSquare,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";

// recharts is heavy — load the chart only when this page renders.
const RatingsChart = dynamic(() => import("./ratings-chart").then((m) => m.RatingsChart), {
  ssr: false,
  loading: () => <div className="bg-foreground/5 h-full w-full animate-pulse rounded-md" />,
});

import { StatCard } from "@/components/dashboard/stat-card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { DataTable, type Column } from "@/components/ui";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import type { MessageRatingListResponse, MessageRatingWithDetails, RatingSummary } from "@/types";
import { useLocale, useTranslations } from "next-intl";

const PAGE_SIZE = 50;
type RatingFilter = "all" | "positive" | "negative";


export default function AdminRatingsPage() {
  const t = useTranslations("admin");
  const locale = useLocale();
  const [summary, setSummary] = useState<RatingSummary | null>(null);
  const [ratings, setRatings] = useState<MessageRatingListResponse | null>(null);
  const [filter, setFilter] = useState<RatingFilter>("all");
  const [commentsOnly, setCommentsOnly] = useState(false);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exportFormat, setExportFormat] = useState<"json" | "csv">("csv");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const ratingsParams = new URLSearchParams({
        skip: String(page * PAGE_SIZE),
        limit: String(PAGE_SIZE),
        with_comments_only: String(commentsOnly),
      });
      if (filter !== "all") {
        ratingsParams.set("rating_filter", filter === "positive" ? "1" : "-1");
      }
      const [summaryData, ratingsData] = await Promise.all([
        apiClient.get<RatingSummary>("/admin/ratings/summary?days=30"),
        apiClient.get<MessageRatingListResponse>(`/admin/ratings?${ratingsParams}`),
      ]);
      setSummary(summaryData);
      setRatings(ratingsData);
    } catch {
      /* ignore — empty state handles errors */
    } finally {
      setLoading(false);
    }
  }, [page, filter, commentsOnly]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = () => {
    const params = new URLSearchParams({ export_format: exportFormat });
    if (filter !== "all") params.set("rating_filter", filter === "positive" ? "1" : "-1");
    if (commentsOnly) params.set("with_comments_only", "true");
    window.open(`/api/admin/ratings/export?${params}`, "_blank");
  };

  const totalPages = ratings ? Math.ceil(ratings.total / PAGE_SIZE) : 0;
  const approvalRate =
    summary && summary.total_ratings > 0
      ? Math.round((summary.like_count / summary.total_ratings) * 100)
      : null;

  const columns: Column<MessageRatingWithDetails>[] = [
    {
      key: "date",
      header: t("date"),
      className: "whitespace-nowrap",
      cell: (r) => (
        <span className="text-muted-foreground font-mono text-xs tabular-nums">
          {formatDate(r.created_at, locale === "zh" ? "zh-CN" : locale)}
        </span>
      ),
    },
    {
      key: "rating",
      header: t("rating"),
      cell: (r) =>
        r.rating === 1 ? (
          <span className="bg-muted text-foreground inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase">
            <ThumbsUp className="h-3 w-3" />
            {t("like")}
          </span>
        ) : (
          <span className="bg-muted text-foreground inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase">
            <ThumbsDown className="h-3 w-3" />
            {t("dislike")}
          </span>
        ),
    },
    {
      key: "comment",
      header: t("comment"),
      className: "max-w-[180px]",
      cell: (r) => (
        <span className="text-foreground block truncate text-xs">
          {r.comment || <span className="text-muted-foreground">—</span>}
        </span>
      ),
    },
    {
      key: "message",
      header: t("message"),
      className: "max-w-[260px]",
      cell: (r) => (
        <span className="text-muted-foreground block truncate text-xs">
          {r.message_content || "—"}
        </span>
      ),
    },
    {
      key: "user",
      header: t("user"),
      className: "whitespace-nowrap",
      cell: (r) => (
        <span className="text-foreground text-xs">{r.user_name || r.user_email || "—"}</span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      cell: (r) =>
        r.conversation_id ? (
          <Link
            href={`${ROUTES.CHAT}?id=${r.conversation_id}`}
            className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 font-mono text-[11px] tracking-wider uppercase transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
            {t("view")}
          </Link>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted-foreground text-sm">
          {t("ratingsIntro")}
        </p>
        <div className="flex items-center gap-2">
          <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as "json" | "csv")}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="json">JSON</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-3.5 w-3.5" />
            {t("export")}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={t("totalRatings")}
          value={loading ? "—" : (summary?.total_ratings ?? 0).toLocaleString()}
          loading={loading}
        />
        <StatCard
          label={t("likes")}
          value={loading ? "—" : (summary?.like_count ?? 0).toLocaleString()}
          icon={ThumbsUp}
          loading={loading}
        />
        <StatCard
          label={t("dislikes")}
          value={loading ? "—" : (summary?.dislike_count ?? 0).toLocaleString()}
          icon={ThumbsDown}
          loading={loading}
        />
        <StatCard
          label={t("approvalRate")}
          value={loading ? "—" : approvalRate !== null ? `${approvalRate}%` : "—"}
          icon={TrendingUp}
          loading={loading}
        />
      </div>

      {!loading && summary && summary.ratings_by_day.length > 0 && (
        <section className="border-border bg-card rounded-xl border p-6">
          <h2 className="text-foreground text-sm font-semibold">{t("ratingsPerDay")}</h2>
          <p className="text-muted-foreground text-xs">{t("ratingsPerDayDesc")}</p>
          <div className="mt-5 h-56">
            <RatingsChart data={summary.ratings_by_day} />
          </div>
          <div className="mt-3 flex items-center gap-5">
            <span className="flex items-center gap-1.5">
              <span className="bg-foreground/75 h-2.5 w-2.5 rounded-full" />
              <span className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
                {t("likes")}
              </span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="bg-foreground/30 h-2.5 w-2.5 rounded-full" />
              <span className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
                {t("dislikes")}
              </span>
            </span>
          </div>
        </section>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Select
            value={filter}
            onValueChange={(v) => {
              setFilter(v as RatingFilter);
              setPage(0);
            }}
          >
            <SelectTrigger className="w-36 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("allRatings")}</SelectItem>
              <SelectItem value="positive">{t("likesOnly")}</SelectItem>
              <SelectItem value="negative">{t("dislikesOnly")}</SelectItem>
            </SelectContent>
          </Select>
          <label className="flex cursor-pointer items-center gap-2 text-xs">
            <Checkbox
              checked={commentsOnly}
              onCheckedChange={(v) => {
                setCommentsOnly(!!v);
                setPage(0);
              }}
            />
            <span className="text-muted-foreground">{t("withCommentsOnly")}</span>
          </label>
        </div>
        {ratings && !loading && (
          <span className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
            {t("results", { count: ratings.total })}
          </span>
        )}
      </div>

      <DataTable
        columns={columns}
        rows={ratings?.items}
        getRowKey={(r) => r.id}
        loading={loading}
        skeletonRows={8}
        empty={
          <div className="py-8">
            <MessageSquare className="text-muted-foreground mx-auto mb-3 h-8 w-8" />
            <p className="text-foreground text-sm">{t("noRatingsFound")}</p>
            <p className="text-muted-foreground mt-1 text-xs">{t("adjustFilters")}</p>
          </div>
        }
      />

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
            {t("pageOfWithTotal", { page: page + 1, pages: totalPages, total: ratings?.total ?? 0 })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              {t("previousPage")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            >
              {t("nextPage")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
