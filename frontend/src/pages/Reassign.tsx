import { useEffect, useState } from "react";
import { admin as adminApi, conversations } from "../api/endpoints";
import { ApiError } from "../api/client";
import type { ConversationOut, LineOut } from "../types";

/** "Repartir": move a conversation from one agent's line to another's -
    rebalancing an overloaded queue, or handing off while someone's out. */
export function Reassign() {
  const [list, setList] = useState<ConversationOut[]>([]);
  const [lines, setLines] = useState<LineOut[]>([]);
  const [notice, setNotice] = useState<string | null>(null);

  function load() {
    conversations.list().then(setList).catch(() => undefined);
    adminApi.lines().then(setLines).catch(() => undefined);
  }

  useEffect(load, []);

  async function reassign(conversationId: string, lineId: string) {
    if (!lineId) return;
    try {
      await conversations.reassign(conversationId, lineId);
      setNotice("Conversation reassigned.");
      load();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Could not reassign");
    }
  }

  const lineLabel = (id: string) => lines.find((l) => l.id === id)?.label ?? "—";

  return (
    <div className="reassign-page">
      <header className="page-header">
        <h2>Distribute</h2>
        <p className="tenue">Move a conversation to another agent's WhatsApp line.</p>
      </header>

      {notice && (
        <div className="notice" onClick={() => setNotice(null)}>
          {notice}
        </div>
      )}

      <table className="lines-table">
        <thead>
          <tr>
            <th>Contact</th>
            <th>Currently on</th>
            <th>Move to</th>
          </tr>
        </thead>
        <tbody>
          {list.map((c) => (
            <tr key={c.id}>
              <td>
                <strong>{c.contact.name}</strong>
                <br />
                <span className="tenue">{c.contact.phone_number}</span>
              </td>
              <td>{lineLabel(c.line_id)}</td>
              <td>
                <select defaultValue="" onChange={(e) => reassign(c.id, e.target.value)}>
                  <option value="" disabled>
                    Pick a line…
                  </option>
                  {lines
                    .filter((l) => l.id !== c.line_id)
                    .map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.label}
                      </option>
                    ))}
                </select>
              </td>
            </tr>
          ))}
          {list.length === 0 && (
            <tr>
              <td colSpan={3} className="tenue">
                No conversations yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
