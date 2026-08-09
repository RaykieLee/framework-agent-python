"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Filter,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";

import {
  Button,
  DataTable,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  type Column,
} from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { cn, formatCurrency } from "@/lib/utils";
import { useLocale } from "next-intl";

interface StripeEvent {
  id: string;
  type: string;
  status: "processed" | "failed" | "pending";
  livemode: boolean;
  customer_email?: string | null;
  amount_cents?: number | null;
  currency?: string | null;
  created_at: string;
  attempts: number;
  last_error?: string | null;
}

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
type StatusFilter = "all" | "processed" | "failed" | "pending";

function formatDateTime(iso: string, locale = "en-US"): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(locale, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatAmount(
  cents: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (typeof cents !== "number") return "—";
  return formatCurrency(cents, currency ?? "USD");
}

const STUB_EVENTS: StripeEvent[] = [
  {
    id: "evt_3PqWzL2eZvKYlo2C0K",
    type: "invoice.payment_succeeded",
    status: "processed",
    livemode: true,
    customer_email: "maya@lumenlabs.co",
    amount_cents: 2900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzM2eZvKYlo2DRT",
    type: "customer.subscription.updated",
    status: "processed",
    livemode: true,
    customer_email: "jonas@stash.ai",
    created_at: new Date(Date.now() - 1000 * 60 * 47).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzN2eZvKYlo2EX7",
    type: "invoice.payment_failed",
    status: "failed",
    livemode: true,
    customer_email: "ops@northwind.io",
    amount_cents: 9900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    attempts: 3,
    last_error: "Card declined: insufficient_funds",
  },
  {
    id: "evt_3PqWzO2eZvKYlo2F8M",
    type: "checkout.session.completed",
    status: "processed",
    livemode: true,
    customer_email: "priya@example.io",
    amount_cents: 2900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzP2eZvKYlo2GZQ",
    type: "customer.subscription.deleted",
    status: "processed",
    livemode: false,
    customer_email: "test@example.com",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzQ2eZvKYlo2HHb",
    type: "invoice.created",
    status: "pending",
    livemode: true,
    customer_email: "billing@megacorp.com",
    amount_cents: 49900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
    attempts: 0,
  },
];

export default function StripeEventsPage() {
  const zh = useLocale() === "zh";
  const [events, setEvents] = useState<StripeEvent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [pageSize, setPageSize] = useState(50);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<StripeEvent | null>(null);
  const [usingStub, setUsingStub] = useState(false);
  const [replaying, setReplaying] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiClient
        .get<{ items: StripeEvent[] }>("/admin/stripe-events?limit=500")
        .catch(() => null);
      if (data) {
        setEvents(data.items);
        setUsingStub(false);
      } else {
        setEvents(STUB_EVENTS);
        setUsingStub(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    setPage(0);
  }, [search, statusFilter, pageSize]);

  const filtered = useMemo(() => {
    if (!events) return [];
    const q = search.trim().toLowerCase();
    return events
      .filter((e) => {
        if (statusFilter !== "all" && e.status !== statusFilter) return false;
        if (q) {
          return (
            e.id.toLowerCase().includes(q) ||
            e.type.toLowerCase().includes(q) ||
            (e.customer_email ?? "").toLowerCase().includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [events, search, statusFilter]);

  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pageItems = useMemo(
    () => filtered.slice(page * pageSize, (page + 1) * pageSize),
    [filtered, page, pageSize],
  );

  const handleReplay = async (evt: StripeEvent) => {
    if (usingStub) {
      toast.info(zh ? "演示模式：需要接通后端接口（POST /admin/stripe-events/{id}/replay）" : "Demo mode — backend wiring required (POST /admin/stripe-events/{id}/replay)");
      return;
    }
    setReplaying(evt.id);
    try {
      await apiClient.post(`/admin/stripe-events/${evt.id}/replay`);
      toast.success(zh ? `已重放 ${evt.type}` : `Replayed ${evt.type}`);
      await load();
    } catch {
      toast.error(zh ? "重放失败" : "Replay failed");
    } finally {
      setReplaying(null);
    }
  };

  const columns: Column<StripeEvent>[] = [
    {
      key: "type",
      header: zh ? "事件" : "Event",
      cell: (e) => (
        <div className="min-w-0">
          <p className="text-foreground truncate font-medium">{e.type}</p>
          <p className="text-muted-foreground truncate font-mono text-xs">{e.id}</p>
        </div>
      ),
    },
    {
      key: "customer",
      header: zh ? "客户" : "Customer",
      hideBelow: "md",
      cell: (e) => <span className="text-muted-foreground">{e.customer_email ?? "—"}</span>,
    },
    {
      key: "amount",
      header: zh ? "金额" : "Amount",
      align: "right",
      hideBelow: "sm",
      className: "tabular-nums",
      cell: (e) => formatAmount(e.amount_cents, e.currency),
    },
    {
      key: "status",
      header: zh ? "状态" : "Status",
      cell: (e) => <StatusBadge status={e.status} attempts={e.attempts} zh={zh} />,
    },
    {
      key: "created",
      header: zh ? "时间" : "Time",
      hideBelow: "lg",
      cell: (e) => (
        <span className="text-muted-foreground text-xs whitespace-nowrap">
          {formatDateTime(e.created_at, zh ? "zh-CN" : "en-US")}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      className: "w-px",
      cell: (e) => (
        <Button
          variant="ghost"
          size="sm"
          disabled={replaying === e.id}
          onClick={(ev) => {
            ev.stopPropagation();
            handleReplay(e);
          }}
          aria-label={zh ? "重放事件" : "Replay event"}
        >
          <RefreshCw className={cn("h-3.5 w-3.5", replaying === e.id && "animate-spin")} />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {usingStub && (
        <div className="border-border bg-muted flex items-start gap-3 rounded-xl border p-3">
          <Filter className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
          <div className="min-w-0 flex-1 text-xs">
            <p className="text-foreground font-medium">{zh ? "演示数据" : "Demo data"}</p>
            <p className="text-muted-foreground mt-0.5">
              {zh ? "需要接通后端接口：" : "Backend wiring required. Expected: "}<code className="font-mono">GET /admin/stripe-events</code>,{" "}
              <code className="font-mono">POST /admin/stripe-events/&#123;id&#125;/replay</code>.
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder={zh ? "搜索 ID、类型或客户…" : "Search id, type, customer…"}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{zh ? "全部状态" : "All statuses"}</SelectItem>
            <SelectItem value="processed">{zh ? "已处理" : "Processed"}</SelectItem>
            <SelectItem value="failed">{zh ? "失败" : "Failed"}</SelectItem>
            <SelectItem value="pending">{zh ? "待处理" : "Pending"}</SelectItem>
          </SelectContent>
        </Select>

        <Select value={String(pageSize)} onValueChange={(v) => setPageSize(Number(v))}>
          <SelectTrigger className="w-[110px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {zh ? `每页 ${n} 条` : `${n} / page`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          {zh ? "刷新" : "Refresh"}
        </Button>
      </div>

      <div className="text-muted-foreground text-xs">{zh ? `共 ${total} 条` : `${total} total`}</div>

      <DataTable
        columns={columns}
        rows={pageItems}
        getRowKey={(e) => e.id}
        loading={loading && events === null}
        onRowClick={(e) => setSelected(e)}
        empty={zh ? "没有匹配的事件。" : "No events match."}
      />

      {total > 0 && (
        <div className="border-border bg-card flex items-center justify-between rounded-xl border px-4 py-3">
          <span className="text-muted-foreground text-sm">
            {zh ? `第 ${page * pageSize + 1}–${Math.min(total, (page + 1) * pageSize)} 条，共 ${total} 条` : `${page * pageSize + 1}–${Math.min(total, (page + 1) * pageSize)} of ${total}`}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              aria-label={zh ? "上一页" : "Previous page"}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-muted-foreground px-2 text-sm tabular-nums">
              {page + 1} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1 || loading}
              aria-label={zh ? "下一页" : "Next page"}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <EventDetailDialog
        event={selected}
        replaying={selected ? replaying === selected.id : false}
        onReplay={handleReplay}
        onClose={() => setSelected(null)}
        zh={zh}
      />
    </div>
  );
}

function StatusBadge({ status, attempts, zh }: { status: StripeEvent["status"]; attempts: number; zh: boolean }) {
  const suffix = attempts > 1 ? ` · ${attempts}×` : "";
  const styles: Record<StripeEvent["status"], string> = {
    processed: "border-border bg-muted text-foreground",
    failed: "border-destructive/30 bg-destructive/10 text-destructive",
    pending: "border-border bg-muted text-muted-foreground",
  };
  const label = zh ? { processed: "已处理", failed: "失败", pending: "待处理" }[status] : { processed: "Processed", failed: "Failed", pending: "Pending" }[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        styles[status],
      )}
    >
      {label}
      {status !== "pending" ? suffix : ""}
    </span>
  );
}

function EventDetailDialog({
  event,
  replaying,
  onReplay,
  onClose,
  zh,
}: {
  event: StripeEvent | null;
  replaying: boolean;
  onReplay: (e: StripeEvent) => void;
  onClose: () => void;
  zh: boolean;
}) {
  return (
    <Dialog open={event !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="bg-card border-border max-w-2xl rounded-xl">
        {event && (
          <>
            <DialogHeader>
              <DialogTitle className="font-mono text-sm break-all">{event.type}</DialogTitle>
              <DialogDescription className="font-mono text-xs break-all">
                {event.id}
              </DialogDescription>
            </DialogHeader>

            <dl className="grid gap-3 text-xs sm:grid-cols-2">
              <KV label={zh ? "模式" : "Mode"} value={event.livemode ? "live" : "test"} />
              <KV label={zh ? "状态" : "Status"} value={event.status} />
              <KV label={zh ? "尝试次数" : "Attempts"} value={String(event.attempts)} />
              <KV label={zh ? "创建时间" : "Created"} value={formatDateTime(event.created_at, zh ? "zh-CN" : "en-US")} />
              {event.customer_email && <KV label={zh ? "客户" : "Customer"} value={event.customer_email} />}
              {typeof event.amount_cents === "number" && (
                <KV label={zh ? "金额" : "Amount"} value={formatAmount(event.amount_cents, event.currency)} />
              )}
              {event.last_error && (
                <KV label={zh ? "最近错误" : "Last error"} value={event.last_error} accent="danger" />
              )}
            </dl>

            <div className="space-y-1.5">
              <p className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
                {zh ? "载荷" : "Payload"}
              </p>
              <pre className="bg-muted border-border text-foreground max-h-64 overflow-auto rounded-xl border p-3 font-mono text-xs leading-relaxed">
                {JSON.stringify(event, null, 2)}
              </pre>
            </div>

            <DialogFooter className="gap-2 sm:justify-between">
              <a
                href={`https://dashboard.stripe.com/${event.livemode ? "" : "test/"}events/${event.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 text-xs"
              >
                {zh ? "在 Stripe 中打开" : "Open in Stripe"}
                <ExternalLink className="h-3 w-3" />
              </a>
              <Button size="sm" variant="outline" disabled={replaying} onClick={() => onReplay(event)}>
                <RefreshCw className={cn("h-3.5 w-3.5", replaying && "animate-spin")} />
                {zh ? "重放" : "Replay"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function KV({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "danger";
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
        {label}
      </dt>
      <dd className={cn("break-all", accent === "danger" ? "text-destructive" : "text-foreground")}>
        {value}
      </dd>
    </div>
  );
}
