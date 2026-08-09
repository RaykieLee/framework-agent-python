"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Database,
  HardDrive,
  RefreshCw,
  Server,
  Wifi,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { LoadingState } from "@/components/states";
import { Button } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { cn, getErrorMessage } from "@/lib/utils";
import { useLocale } from "next-intl";

type ServiceStatus = "operational" | "degraded" | "outage" | "unknown";

interface ServiceHealth {
  key: string;
  name: string;
  description: string;
  icon: LucideIcon;
  status: ServiceStatus;
  uptime90d: number;
  latencyMs?: number;
  detail?: string;
}

interface BackendHealthResp {
  status?: string;
  database?: { status?: string; latency_ms?: number };
  redis?: { status?: string; latency_ms?: number };
  vector_store?: { status?: string; latency_ms?: number };
  stripe?: { status?: string };
  llm?: { status?: string; provider?: string };
  worker?: { status?: string };
}

const REFRESH_INTERVAL_MS = 30_000;

function statusFromString(s?: string): ServiceStatus {
  if (!s) return "unknown";
  const v = s.toLowerCase();
  if (["ok", "up", "operational", "ready", "healthy"].includes(v)) return "operational";
  if (["degraded", "slow"].includes(v)) return "degraded";
  if (["down", "outage", "fail", "failed", "error"].includes(v)) return "outage";
  return "unknown";
}

function buildServices(resp: BackendHealthResp | null, zh: boolean): ServiceHealth[] {
  const overall = statusFromString(resp?.status);
  return [
    {
      key: "api",
      name: "API",
      description: zh ? "REST + WebSocket 网关" : "REST + WebSocket gateway",
      icon: Server,
      status: overall === "unknown" ? "operational" : overall,
      uptime90d: 99.94,
    },
    {
      key: "database",
      name: zh ? "数据库" : "Database",
      description: zh ? "PostgreSQL 主数据库" : "PostgreSQL primary",
      icon: Database,
      status: statusFromString(resp?.database?.status),
      uptime90d: 99.97,
      latencyMs: resp?.database?.latency_ms,
    },
    {
      key: "redis",
      name: "Redis",
      description: zh ? "缓存与队列代理" : "Cache & queue broker",
      icon: Zap,
      status: statusFromString(resp?.redis?.status),
      uptime90d: 99.96,
      latencyMs: resp?.redis?.latency_ms,
    },
    {
      key: "vector",
      name: zh ? "向量存储" : "Vector store",
      description: zh ? "RAG 向量嵌入后端" : "RAG embeddings backend",
      icon: HardDrive,
      status: statusFromString(resp?.vector_store?.status),
      uptime90d: 99.91,
      latencyMs: resp?.vector_store?.latency_ms,
    },
    {
      key: "llm",
      name: zh ? "LLM 提供商" : "LLM provider",
      description: resp?.llm?.provider ? `${zh ? "提供商" : "Provider"}: ${resp.llm.provider}` : zh ? "默认模型 API" : "Default model API",
      icon: Cpu,
      status: statusFromString(resp?.llm?.status),
      uptime90d: 99.87,
    },
    {
      key: "stripe",
      name: "Stripe API",
      description: zh ? "账单与支付" : "Billing & payments",
      icon: Wifi,
      status: statusFromString(resp?.stripe?.status),
      uptime90d: 99.99,
    },
    {
      key: "worker",
      name: zh ? "后台任务" : "Background worker",
      description: zh ? "文档导入与同步任务" : "Document ingestion + sync jobs",
      icon: Activity,
      status: statusFromString(resp?.worker?.status),
      uptime90d: 99.89,
    },
  ];
}

const STATUS_DOT: Record<ServiceStatus, string> = {
  operational: "bg-chart",
  degraded: "bg-muted-foreground",
  outage: "bg-destructive",
  unknown: "bg-muted-foreground",
};

const STATUS_LABEL: Record<ServiceStatus, string> = {
  operational: "Operational",
  degraded: "Degraded",
  outage: "Outage",
  unknown: "Unknown",
};

const STATUS_TEXT: Record<ServiceStatus, string> = {
  operational: "text-foreground",
  degraded: "text-foreground",
  outage: "text-destructive",
  unknown: "text-muted-foreground",
};

export default function SystemHealthPage() {
  const zh = useLocale() === "zh";
  const [resp, setResp] = useState<BackendHealthResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auto, setAuto] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      // Try the detailed readiness endpoint first; fall back to /health.
      const ready = await apiClient.get<BackendHealthResp>("/health/ready").catch(() => null);
      const data = ready ?? (await apiClient.get<BackendHealthResp>("/health"));
      setResp(data);
      setLastChecked(new Date());
    } catch (err) {
      setError(getErrorMessage(err, zh ? "获取健康状态失败" : "Failed to fetch health"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!auto) return;
    const id = window.setInterval(load, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [auto]);

  const services = useMemo(() => buildServices(resp, zh), [resp, zh]);
  const overall: ServiceStatus = useMemo(() => {
    if (services.some((s) => s.status === "outage")) return "outage";
    if (services.some((s) => s.status === "degraded")) return "degraded";
    if (services.every((s) => s.status === "operational" || s.status === "unknown"))
      return "operational";
    return "unknown";
  }, [services]);

  const overallLabel =
    overall === "operational"
      ? zh ? "所有系统运行正常" : "All systems operational"
      : overall === "outage"
        ? zh ? "存在服务中断" : "Active outage"
        : overall === "degraded"
          ? zh ? "性能下降" : "Degraded performance"
          : zh ? "状态未知" : "Status unknown";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setAuto((a) => !a)}
          className={cn(auto && "bg-muted")}
        >
          <span
            aria-hidden
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              auto ? "bg-chart" : "bg-muted-foreground",
            )}
          />
          {zh ? "自动刷新" : "Auto-refresh"} {auto ? (zh ? "开启" : "on") : (zh ? "关闭" : "off")}
        </Button>
        <Button size="sm" variant="outline" onClick={load}>
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          {zh ? "刷新" : "Refresh"}
        </Button>
      </div>

      <section className="border-border bg-card rounded-xl border p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="bg-muted text-foreground inline-flex h-10 w-10 items-center justify-center rounded-lg">
              {overall === "outage" ? (
                <AlertCircle className="h-5 w-5" />
              ) : (
                <CheckCircle2 className="h-5 w-5" />
              )}
            </span>
            <div>
              <p className="text-muted-foreground text-xs">{zh ? "总体状态" : "Overall status"}</p>
              <div className="mt-1 flex items-center gap-2">
                <span
                  aria-hidden
                  className={cn("h-2 w-2 rounded-full", STATUS_DOT[overall])}
                />
                <p className="text-foreground text-base font-semibold">{overallLabel}</p>
              </div>
            </div>
          </div>
          {lastChecked && (
            <span className="text-muted-foreground text-xs">
              {zh ? "检查于" : "Checked"} {lastChecked.toLocaleTimeString()}
            </span>
          )}
        </div>
      </section>

      {loading && !resp ? (
        <LoadingState variant="stats" rows={6} />
      ) : error ? (
        <div className="border-border bg-card rounded-xl border p-8 text-center">
          <AlertCircle className="text-destructive mx-auto h-6 w-6" />
          <p className="text-foreground mt-3 text-sm font-medium">{zh ? "无法获取健康状态" : "Couldn't fetch health"}</p>
          <p className="text-muted-foreground mt-1 text-xs">{error}</p>
        </div>
      ) : (
        <section className="border-border bg-card rounded-xl border">
          <div className="border-border border-b px-5 py-4">
            <h2 className="text-foreground text-sm font-semibold">{zh ? "服务" : "Services"}</h2>
            <p className="text-muted-foreground text-xs">
              {zh ? "各项后端服务的实时就绪状态，每 30 秒自动刷新。" : "Live readiness for each backing service. Auto-refreshes every 30s."}
            </p>
          </div>
          <ul className="divide-border divide-y">
            {services.map((s) => (
              <li key={s.key} className="flex items-center gap-3 px-5 py-4">
                <span className="bg-muted text-muted-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                  <s.icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-medium">{s.name}</p>
                  <p className="text-muted-foreground truncate text-xs">{s.description}</p>
                </div>
                <div className="hidden text-right sm:block">
                  <p className="text-foreground text-xs tabular-nums">
                    {s.uptime90d.toFixed(2)}%
                  </p>
                  <p className="text-muted-foreground text-[11px]">
                    90d{typeof s.latencyMs === "number" ? ` · p50 ${s.latencyMs}ms` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2 pl-1">
                  <span
                    aria-hidden
                    className={cn("h-2 w-2 rounded-full", STATUS_DOT[s.status])}
                  />
                  <span
                    className={cn(
                      "text-xs font-medium whitespace-nowrap",
                      STATUS_TEXT[s.status],
                    )}
                  >
                    {zh ? ({ operational: "运行正常", degraded: "性能下降", outage: "服务中断", unknown: "未知" } as const)[s.status] : STATUS_LABEL[s.status]}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="text-muted-foreground text-xs">
        {zh ? "后端待完善项：" : "Backend wishlist: "}<code className="font-mono">/health/ready</code>{zh ? " 返回各服务详情。目前显示的 90 天可用率为示例数据。" : " with per-service detail. 90d uptime is currently illustrative."}
      </p>
    </div>
  );
}
