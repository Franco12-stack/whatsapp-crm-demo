import { useEffect, useState } from "react";
import { support } from "../api/endpoints";
import { ApiError } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { EstadoTicket, PrioridadTicket, SupportTicketOut } from "../types";

const COLUMNS: { state: EstadoTicket; label: string }[] = [
  { state: "open", label: "Open" },
  { state: "in_progress", label: "In progress" },
  { state: "resolved", label: "Resolved" },
];

const PRIORITY_ORDER: Record<PrioridadTicket, number> = { urgent: 0, high: 1, medium: 2, low: 3 };

export function Support() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [tickets, setTickets] = useState<SupportTicketOut[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<PrioridadTicket>("medium");
  const [notice, setNotice] = useState<string | null>(null);

  function load() {
    support.list().then(setTickets).catch(() => undefined);
  }

  useEffect(load, []);

  async function createTicket() {
    if (title.trim().length < 3 || description.trim().length < 5) return;
    try {
      await support.create(title.trim(), description.trim(), priority);
      setTitle("");
      setDescription("");
      setPriority("medium");
      load();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Could not create the ticket");
    }
  }

  async function move(ticket: SupportTicketOut, state: EstadoTicket) {
    try {
      await support.update(ticket.id, state, ticket.admin_note ?? undefined);
      load();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Could not update the ticket");
    }
  }

  return (
    <div className="support-page">
      <header className="page-header">
        <h2>Support</h2>
        <p className="tenue">Report a problem, track it through to resolved.</p>
      </header>

      <section className="support-form">
        <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <textarea
          rows={2}
          placeholder="What happened?"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <select value={priority} onChange={(e) => setPriority(e.target.value as PrioridadTicket)}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <button onClick={createTicket}>Report</button>
      </section>

      {notice && (
        <div className="notice" onClick={() => setNotice(null)}>
          {notice}
        </div>
      )}

      <div className="kanban">
        {COLUMNS.map((col) => {
          const items = tickets
            .filter((t) => t.state === col.state)
            .sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
          return (
            <div key={col.state} className="kanban-col">
              <div className="kanban-col-head">
                {col.label}
                <span className="kanban-count">{items.length}</span>
              </div>
              <div className="kanban-col-body">
                {items.map((t) => (
                  <div key={t.id} className="ticket-card">
                    <div className="ticket-card-top">
                      <strong>{t.title}</strong>
                      <span className={`tag priority-${t.priority}`}>{t.priority}</span>
                    </div>
                    <p className="tenue">{t.description}</p>
                    <p className="tenue">by {t.reported_by.full_name}</p>
                    {t.admin_note && <p className="ticket-note">{t.admin_note}</p>}
                    {isAdmin && (
                      <div className="ticket-actions">
                        {COLUMNS.filter((c) => c.state !== t.state).map((c) => (
                          <button key={c.state} className="secondary" onClick={() => move(t, c.state)}>
                            → {c.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {items.length === 0 && <p className="tenue">Nothing here.</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
