import { useEffect, useState } from "react";
import { dashboard } from "../api/endpoints";
import type { AgentStatusOut, AlertOut } from "../types";
import { avatarHue, initials } from "../utils";

function warmupStage(daysConnected: number): { label: string; dot: string } {
  if (daysConnected >= 30) return { label: "fully warmed up", dot: "dot-ok" };
  if (daysConnected >= 7) return { label: "warming up", dot: "dot-warn" };
  return { label: "just connected", dot: "dot-new" };
}

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
      <header className="page-header">
        <h2>Team status</h2>
        <p className="tenue">Live usage against each line's effective limit, not the raw policy.</p>
      </header>
      <section>
        <div className="agent-cards">
          {agents.map((a) => (
            <div key={a.user.id} className="agent-card">
              <div className="agent-card-head">
                <span
                  className="avatar"
                  style={{ background: `hsl(${avatarHue(a.user.full_name)}, 45%, 32%)` }}
                >
                  {initials(a.user.full_name)}
                </span>
                <div>
                  <strong>{a.user.full_name}</strong>
                  {a.line && (
                    <div className="status-line">
                      <span className={`dot ${warmupStage(a.line.days_connected).dot}`} />
                      <span className="tenue">{warmupStage(a.line.days_connected).label}</span>
                    </div>
                  )}
                </div>
              </div>
              {a.line ? (
                <>
                  <p className="tenue line-label">{a.line.label}</p>
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
                  <div className="agent-card-stats">
                    <span>
                      <strong>{a.open_conversations}</strong> open
                    </span>
                    <span>
                      <strong>{a.messages_today}</strong> sent today
                    </span>
                  </div>
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
