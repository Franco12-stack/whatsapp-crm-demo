import { useEffect, useState } from "react";
import { metrics as metricsApi } from "../api/endpoints";
import type { MetricsOut } from "../types";

function StatTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="stat-tile">
      <span className="tenue">{label}</span>
      <strong>{value}</strong>
      {sub && <span className="tenue">{sub}</span>}
    </div>
  );
}

/** Used for both "Mis métricas" (own numbers) and "Informe" (team numbers) -
    same shape, different scope, so the two screens can't quietly drift on
    what counts as "this week." */
export function Metrics({ scope }: { scope: "me" | "team" }) {
  const [data, setData] = useState<MetricsOut | null>(null);

  useEffect(() => {
    const fetcher = scope === "me" ? metricsApi.mine : metricsApi.team;
    fetcher().then(setData).catch(() => undefined);
  }, [scope]);

  if (!data) return <p className="tenue" style={{ padding: 24 }}>Loading…</p>;

  const warmPct = data.conversations_total
    ? Math.round((data.conversations_warm / data.conversations_total) * 100)
    : 0;

  return (
    <div className="metrics-page">
      <header className="page-header">
        <h2>{scope === "me" ? "My metrics" : "Team report"}</h2>
        <p className="tenue">
          {scope === "me" ? "Your activity across every module." : "Aggregated across every agent and line."}
        </p>
      </header>

      <section className="stat-grid">
        <StatTile label="Messages today" value={data.messages_today} />
        <StatTile label="Messages this week" value={data.messages_this_week} />
        <StatTile label="Messages this month" value={data.messages_this_month} />
        <StatTile label="Calls logged" value={data.calls_logged} />
        <StatTile label="Broadcasts sent" value={data.broadcasts_sent} />
        <StatTile label="Open support tickets" value={data.tickets_open} />
      </section>

      <section className="conversations-split">
        <h3>Conversations ({data.conversations_total})</h3>
        <div className="split-bar">
          <div className="split-bar-warm" style={{ width: `${warmPct}%` }} />
        </div>
        <div className="split-legend">
          <span><span className="dot dot-ok" /> {data.conversations_warm} warm</span>
          <span><span className="dot" style={{ background: "var(--danger)" }} /> {data.conversations_cold} cold</span>
        </div>
      </section>
    </div>
  );
}
