{% raw %}"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Activity } from "lucide-react";

import { SegmentedControl } from "@/components/dashboard/segmented-control";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { apiClient, ApiError } from "@/lib/api-client";
import { getErrorMessage } from "@/lib/utils";
import { useLocale, useTranslations } from "next-intl";

// Recharts loads on demand — keeps it out of the dashboard's initial bundle.
const UsageTimelineChart = dynamic(
  () => import("@/components/dashboard/usage-timeline-chart").then((m) => m.UsageTimelineChart),
  {
    ssr: false,
    loading: () => <div className="bg-foreground/5 h-full w-full animate-pulse rounded-md" />,
  },
);

interface UsageBucket {
  day: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  credits_charged: number;
  total_calls: number;
}

interface UsageTimelineRead {
  buckets: UsageBucket[];
  days: number;
}

const RANGES = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
] as const;

type Metric = "credits" | "calls" | "tokens";

export function UsageTimeline() {
  const t = useTranslations("dashboard");
  const locale = useLocale();
  const [days, setDays] = useState<number>(30);
  const [metric, setMetric] = useState<Metric>("credits");
  const [data, setData] = useState<UsageBucket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTimeline = useMemo(
    () => async (range: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.get<UsageTimelineRead>(
          `/billing/me/credits/usage/timeline?days=${range}`,
        );
        setData(res.buckets);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setData([]);
        } else {
          setError(getErrorMessage(err, t("loadUsageFailed")));
        }
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    fetchTimeline(days);
  }, [days, fetchTimeline]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.map((b) => ({
      day: b.day,
      label: formatDayLabel(b.day, locale),
      credits: b.credits_charged,
      calls: b.total_calls,
      tokens: b.input_tokens + b.output_tokens,
    }));
  }, [data, days, locale]);

  const totalForMetric = chartData.reduce((sum, p) => sum + (p[metric] as number), 0);

  return (
    <div className="border-border bg-card flex flex-col rounded-xl border p-5 lg:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            {t("usageOverTime")}
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-display text-foreground text-2xl font-bold">
              {totalForMetric.toLocaleString()}
            </span>
            <span className="text-foreground/55 text-sm">
              {t(metric)}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <SegmentedControl
            value={metric}
            onChange={(v) => setMetric(v as Metric)}
            options={[
              { label: t("credits"), value: "credits" },
              { label: t("calls"), value: "calls" },
              { label: t("tokens"), value: "tokens" },
            ]}
          />
          <SegmentedControl
            value={String(days)}
            onChange={(v) => setDays(Number(v))}
            options={RANGES.map((r) => ({ label: r.label, value: String(r.days) }))}
          />
        </div>
      </div>

      <div className="mt-5 h-56 w-full">
        {loading ? (
          <LoadingState variant="dot-pulse" label={t("loadingUsage")} />
        ) : error ? (
          <ErrorState
            title={t("couldntLoadUsage")}
            description={error}
            cta={{ label: t("retry"), onClick: () => fetchTimeline(days) }}
            className="h-full"
          />
        ) : !chartData || chartData.length === 0 ? (
          <EmptyState
            icon={Activity}
            title={t("noUsage")}
            description={t("noUsageDesc")}
            fill
          />
        ) : (
          <UsageTimelineChart chartData={chartData} metric={metric} />
        )}
      </div>
    </div>
  );
}

function formatDayLabel(day: string, locale: string): string {
  const d = new Date(day);
  if (Number.isNaN(d.getTime())) return day;
  return d.toLocaleDateString(locale === "zh" ? "zh-CN" : locale, { month: "short", day: "numeric" });
}
{% endraw %}
