import { useEffect, useState } from "react";
import { dashboard } from "../api/endpoints";
import type { AgentStatusOut, AlertOut } from "../types";

export function SupervisorDashboard() {
  const [agents, setAgents] = useState<AgentStatusOut[]>([]);
  const [alerts, setAlerts] = useState<AlertOut[]>([]);

  function load() {
    dashboard.agents().then(setAgents).catch(() => undefined);
    dashboard.alerts().then(setAlerts).catch(() => undefined);
  }

  useEffect(load, []);
  useEffect(() => {
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  async function ack(id: string) {
    await dashboard.ackAlert(id);
    load();
  }

  return (
    <div className="dashboard">
      <section>
        <h2>Team status</h2>
        <div className="agent-cards">
          {agents.map((a) => (
            <div key={a.user.id} className="agent-card">
              <strong>{a.user.full_name}</strong>
              {a.line ? (
                <>
                  <p className="tenue">{a.line.label}</p>
                  <div className="usage-bar">
                    <div
                      className={`usage-fill ${a.line.usage_percent >= 90 ? "high" : ""}`}
                      style={{ width: `${a.line.usage_percent}%` }}
                    />
                  </div>
                  <p className="tenue">
                    {a.line.usage_percent}% of today's effective limit ({a.line.effective_daily_limit}/day,
                    day {a.line.days_connected} of warm-up)
                  </p>
                  <p className="tenue">
                    {a.open_conversations} open conversations · {a.messages_today} sent today
                  </p>
                </>
              ) : (
                <p className="tenue">No WhatsApp line assigned</p>
              )}
            </div>
          ))}
          {agents.length === 0 && <p className="tenue">No agents yet.</p>}
        </div>
      </section>

      <section>
        <h2>Alerts</h2>
        <div className="alert-list">
          {alerts.map((al) => (
            <div key={al.id} className={`alert-row ${al.kind}`}>
              <div>
                <strong>{al.title}</strong>
                {al.detail && <p className="tenue">{al.detail}</p>}
              </div>
              <button onClick={() => ack(al.id)}>Dismiss</button>
            </div>
          ))}
          {alerts.length === 0 && <p className="tenue">No open alerts. All clear.</p>}
        </div>
      </section>
    </div>
  );
}
