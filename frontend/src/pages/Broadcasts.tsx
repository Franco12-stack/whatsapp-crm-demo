import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { broadcasts, conversations } from "../api/endpoints";
import { ApiError } from "../api/client";
import type { BroadcastRunOut, ConversationOut } from "../types";

export function Broadcasts() {
  const location = useLocation();
  const [list, setList] = useState<ConversationOut[]>([]);
  const [history, setHistory] = useState<BroadcastRunOut[]>([]);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [body, setBody] = useState((location.state as { prefill?: string } | null)?.prefill ?? "");
  const [notice, setNotice] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  function load() {
    conversations.list().then(setList).catch(() => undefined);
    broadcasts.history().then(setHistory).catch(() => undefined);
  }

  useEffect(load, []);

  function toggle(id: string) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    setChecked(new Set(list.map((c) => c.id)));
  }

  async function send(force: boolean) {
    if (checked.size === 0 || !body.trim()) return;
    setSending(true);
    try {
      const result = await broadcasts.send(Array.from(checked), body.trim(), force);
      if (result.skipped_cold.length > 0 && !force) {
        setNotice(
          `Sent to ${result.sent_to.length}. Skipped ${result.skipped_cold.length} cold contact(s): ` +
            result.skipped_cold.map((c) => c.contact_name).join(", ") +
            `. Use "Send to everyone anyway" to override.`,
        );
      } else {
        setNotice(`Sent to ${result.sent_to.length} conversation(s).`);
      }
      setChecked(new Set());
      setBody("");
      load();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Could not send broadcast");
    } finally {
      setSending(false);
    }
  }

  const warmCount = Array.from(checked)
    .map((id) => list.find((c) => c.id === id))
    .filter((c) => c && !c.is_warm).length;

  return (
    <div className="broadcasts-page">
      <header className="page-header">
        <h2>Broadcasts</h2>
        <p className="tenue">
          Cold contacts (no prior reply) are skipped by default — opening many cold conversations at
          once is the clearest spam signal there is.
        </p>
      </header>

      <div className="broadcasts-layout">
        <section className="broadcasts-picker">
          <div className="broadcasts-picker-head">
            <h3>Recipients ({checked.size} selected)</h3>
            <button className="link-btn" onClick={selectAll}>
              Select all
            </button>
          </div>
          <div className="picker-list">
            {list.map((c) => (
              <label key={c.id} className="picker-row">
                <input type="checkbox" checked={checked.has(c.id)} onChange={() => toggle(c.id)} />
                <span>{c.contact.name}</span>
                <span className={`tag ${c.is_warm ? "warm" : "cold"}`}>{c.is_warm ? "warm" : "cold"}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="broadcasts-compose">
          <h3>Message</h3>
          <textarea
            rows={6}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your broadcast message..."
          />
          {warmCount > 0 && (
            <p className="tenue">{warmCount} selected contact(s) are cold and will be skipped unless forced.</p>
          )}
          <div className="actions">
            <button onClick={() => send(false)} disabled={sending}>
              Send (skip cold)
            </button>
            <button className="secondary" onClick={() => send(true)} disabled={sending}>
              Send to everyone anyway
            </button>
          </div>
          {notice && (
            <div className="notice" onClick={() => setNotice(null)}>
              {notice}
            </div>
          )}
        </section>
      </div>

      <section className="broadcasts-history">
        <h3>History</h3>
        <table className="lines-table">
          <thead>
            <tr>
              <th>Message</th>
              <th>Sent by</th>
              <th>Sent</th>
              <th>Skipped cold</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.id}>
                <td className="broadcast-body-cell">{h.body}</td>
                <td>{h.sent_by.full_name}</td>
                <td>{h.sent_count}</td>
                <td>
                  {h.skipped_cold_count}
                  {h.forced && <span className="tag cold" style={{ marginLeft: 6 }}>forced</span>}
                </td>
                <td className="tenue">{new Date(h.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr>
                <td colSpan={5} className="tenue">
                  No broadcasts sent yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
