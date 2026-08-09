"use client";

import { useTranslations } from "next-intl";
import { McpConnectionsManager } from "@/components/settings/mcp-connections-manager";

export default function IntegrationsSettingsPage() {
  const ui = useTranslations("ui");
  return (
    <div className="space-y-6">
      <section className="border-border bg-card rounded-xl border">
        <header className="border-border border-b px-5 py-4">
          <h2 className="text-foreground text-sm font-semibold">{ui("integrations")}</h2>
          <p className="text-muted-foreground mt-1 text-xs">
            {ui("mcpPageDesc")}
          </p>
        </header>
        <div className="px-5 py-5">
          <McpConnectionsManager />
        </div>
      </section>
    </div>
  );
}
