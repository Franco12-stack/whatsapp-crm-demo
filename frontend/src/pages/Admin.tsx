import { useEffect, useState } from "react";
import { admin } from "../api/endpoints";
import type { LineOut } from "../types";

function statusDot(daysConnected: number): string {
  if (daysConnected >= 30) return "dot-ok";
  if (daysConnected >= 7) return "dot-warn";
  return "dot-new";
}

export function Admin() {
  const [lines, setLines] = useState<LineOut[]>([]);

  function load() {
    admin.lines().then(setLines).catch(() => undefined);
  }

  useEffect(load, []);

  async function resetWarmup(id: string) {
    if (!window.confirm("Reset this line's warm-up to day zero? Use this after a reconnect.")) return;
    await admin.resetWarmup(id);
    load();
  }

  async function updatePolicy(line: LineOut, field: keyof LineOut, value: number) {
    await admin.updatePolicy(line.id, {
      policy_daily: field === "policy_daily" ? value : line.policy_daily,
      policy_hourly: field === "policy_hourly" ? value : line.policy_hourly,
      policy_new_chats_daily: field === "policy_new_chats_daily" ? value : line.policy_new_chats_daily,
    });
    load();
  }

  return (
    <div className="admin-panel">
      <header className="page-header">
        <h2>WhatsApp Lines</h2>
        <p className="tenue">
          The effective daily limit shown is <code>min(commercial policy, warm-up tier)</code> -
          a brand-new line stays capped even with a high policy, until it ages past the ramp.
        </p>
      </header>
      <table className="lines-table">
        <thead>
          <tr>
            <th>Line</th>
            <th>Day</th>
            <th>Policy (daily / hourly / new chats)</th>
            <th>Effective today</th>
            <th>Usage</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.id}>
              <td>
                <div className="status-line">
                  <span className={`dot ${statusDot(l.days_connected)}`} />
                  <strong>{l.label}</strong>
                </div>
                <span className="tenue">{l.phone_number}</span>
              </td>
              <td>{l.days_connected}</td>
              <td className="policy-inputs">
                <input
                  type="number"
                  defaultValue={l.policy_daily}
                  onBlur={(e) => updatePolicy(l, "policy_daily", Number(e.target.value))}
                />
                <input
                  type="number"
                  defaultValue={l.policy_hourly}
                  onBlur={(e) => updatePolicy(l, "policy_hourly", Number(e.target.value))}
                />
                <input
                  type="number"
                  defaultValue={l.policy_new_chats_daily}
                  onBlur={(e) => updatePolicy(l, "policy_new_chats_daily", Number(e.target.value))}
                />
              </td>
              <td>{l.effective_daily_limit}/day</td>
              <td>{l.usage_percent}%</td>
              <td>
                <button onClick={() => resetWarmup(l.id)}>Reset warm-up</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
