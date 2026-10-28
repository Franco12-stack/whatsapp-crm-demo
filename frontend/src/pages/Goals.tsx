import { useEffect, useState } from "react";
import { dashboard, goals as goalsApi } from "../api/endpoints";
import { useAuth } from "../hooks/useAuth";
import type { AgentStatusOut, GoalOut } from "../types";

function ProgressBar({ value, target }: { value: number; target: number }) {
  const pct = target > 0 ? Math.min((value / target) * 100, 100) : 0;
  return (
    <div className="usage-bar">
      <div className="usage-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Goals() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [list, setList] = useState<GoalOut[]>([]);
  const [agents, setAgents] = useState<AgentStatusOut[]>([]);

  function load() {
    goalsApi.list().then(setList).catch(() => undefined);
    if (isAdmin) dashboard.agents().then(setAgents).catch(() => undefined);
  }

  useEffect(load, [isAdmin]);

  async function updateGoal(agentId: string, messages: number, convos: number) {
    await goalsApi.set(agentId, messages, convos);
    load();
  }

  const nameFor = (agentId: string) => agents.find((a) => a.user.id === agentId)?.user.full_name ?? "Agent";

  return (
    <div className="goals-page">
      <header className="page-header">
        <h2>Goals</h2>
        <p className="tenue">Monthly targets, with progress computed live.</p>
      </header>

      <div className="goal-cards">
        {list.map((g) => (
          <div key={g.id} className="agent-card">
            <strong>{isAdmin ? nameFor(g.agent_id) : "This month"}</strong>
            <p className="tenue line-label">Messages: {g.progress_messages} / {g.target_messages_month}</p>
            <ProgressBar value={g.progress_messages} target={g.target_messages_month} />
            <p className="tenue line-label">Conversations: {g.progress_conversations} / {g.target_conversations_month}</p>
            <ProgressBar value={g.progress_conversations} target={g.target_conversations_month} />

            {isAdmin && (
              <div className="policy-inputs goal-inputs">
                <input
                  type="number" defaultValue={g.target_messages_month}
                  onBlur={(e) => updateGoal(g.agent_id, Number(e.target.value), g.target_conversations_month)}
                />
                <input
                  type="number" defaultValue={g.target_conversations_month}
                  onBlur={(e) => updateGoal(g.agent_id, g.target_messages_month, Number(e.target.value))}
                />
              </div>
            )}
          </div>
        ))}
        {list.length === 0 && <p className="tenue">No goals set yet.</p>}
      </div>
    </div>
  );
}
