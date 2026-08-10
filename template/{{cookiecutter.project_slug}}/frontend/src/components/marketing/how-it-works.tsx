{% raw %}import { ChevronRight, MessageSquare, UploadCloud, UserPlus } from "lucide-react";
import { useLocale } from "next-intl";

const STEPS = [
  {
    icon: UserPlus,
    title: "Sign up in seconds",
    body: "Create your account, invite your team, and pick the plan that fits. No credit card required for the trial.",
  },
  {
    icon: UploadCloud,
    title: "Connect your data",
    body: "Upload documents or sync from Google Drive, S3, or Notion. Your assistant learns from everything you bring.",
  },
  {
    icon: MessageSquare,
    title: "Start working with AI",
    body: "Ask questions, run workflows, and let the agent take action — across web, mobile, and your favourite chat tools.",
  },
];

export function HowItWorks() {
  const zh = useLocale() === "zh";
  const steps = zh
    ? [
        { icon: UserPlus, title: "几秒完成注册", body: "创建账号、邀请团队并选择合适的套餐。试用期无需信用卡。" },
        { icon: UploadCloud, title: "连接你的数据", body: "上传文档或同步 Google Drive、S3、Notion，助手会学习你带来的内容。" },
        { icon: MessageSquare, title: "开始用 AI 工作", body: "提问、运行工作流，让 Agent 在网页、移动端和聊天工具中执行任务。" },
      ]
    : STEPS;
  return (
    <div className="grid gap-6 md:grid-cols-3 md:gap-8">
      {steps.map((step, i) => (
        <div
          key={step.title}
          className="group border-foreground/15 bg-card lift hover:border-brand/40 relative overflow-hidden rounded-2xl border p-8 transition-colors"
        >
          <div className="text-foreground/[0.07] font-display pointer-events-none absolute -top-2 right-3 text-7xl font-extrabold tabular-nums select-none">
            {i + 1}
          </div>

          <div
            className="text-brand-foreground inline-flex h-12 w-12 items-center justify-center rounded-xl"
            style={{
              background:
                "linear-gradient(135deg, var(--color-brand), oklch(from var(--color-brand) calc(l - 0.14) c h))",
              boxShadow: "0 8px 20px -10px oklch(from var(--color-brand) l c h / 0.9)",
            }}
          >
            <step.icon className="h-5 w-5" />
          </div>

          <h3 className="text-foreground font-display mt-6 text-xl font-bold">{step.title}</h3>
          <p className="text-foreground/65 mt-3 text-sm leading-relaxed">{step.body}</p>

          {i < steps.length - 1 && (
            <div
              aria-hidden
              className="border-border bg-card text-foreground/40 absolute top-1/2 right-[-15px] z-10 hidden h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border md:flex"
            >
              <ChevronRight className="h-4 w-4" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
{% endraw %}
