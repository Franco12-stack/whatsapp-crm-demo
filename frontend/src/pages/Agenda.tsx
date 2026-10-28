import { useEffect, useState } from "react";
import { appointments, conversations } from "../api/endpoints";
import type { AppointmentOut, ConversationOut } from "../types";

export function Agenda() {
  const [list, setList] = useState<AppointmentOut[]>([]);
  const [contacts, setContacts] = useState<ConversationOut[]>([]);
  const [contactId, setContactId] = useState("");
  const [title, setTitle] = useState("");
  const [when, setWhen] = useState("");

  function load() {
    appointments.list().then(setList).catch(() => undefined);
  }

  useEffect(load, []);
  useEffect(() => {
    conversations.list().then(setContacts).catch(() => undefined);
  }, []);

  async function create() {
    if (!contactId || !title.trim() || !when) return;
    await appointments.create(contactId, title.trim(), new Date(when).toISOString());
    setTitle("");
    setWhen("");
    load();
  }

  async function markDone(id: string) {
    await appointments.markDone(id);
    load();
  }

  const upcoming = list.filter((a) => !a.done);
  const done = list.filter((a) => a.done);

  function Row({ a }: { a: AppointmentOut }) {
    const date = new Date(a.scheduled_at);
    const overdue = !a.done && date.getTime() < Date.now();
    return (
      <div className={`agenda-row ${a.done ? "done" : ""} ${overdue ? "overdue" : ""}`}>
        <div className="agenda-row-date">
          <strong>{date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}</strong>
          <span className="tenue">{date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</span>
        </div>
        <div className="agenda-row-body">
          <strong>{a.title}</strong>
          <span className="tenue">{a.contact.name} · {a.contact.phone_number}</span>
        </div>
        {!a.done && <button className="secondary" onClick={() => markDone(a.id)}>Mark done</button>}
        {overdue && <span className="tag cold">overdue</span>}
      </div>
    );
  }

  return (
    <div className="agenda-page">
      <header className="page-header">
        <h2>Agenda</h2>
        <p className="tenue">Follow-ups you scheduled from a conversation.</p>
      </header>

      <section className="agenda-form">
        <select value={contactId} onChange={(e) => setContactId(e.target.value)}>
          <option value="">Pick a contact…</option>
          {contacts.map((c) => (
            <option key={c.id} value={c.contact.id}>{c.contact.name}</option>
          ))}
        </select>
        <input placeholder="e.g. Follow-up call" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
        <button onClick={create}>Schedule</button>
      </section>

      <section>
        <h3>Upcoming ({upcoming.length})</h3>
        <div className="agenda-list">
          {upcoming.map((a) => <Row key={a.id} a={a} />)}
          {upcoming.length === 0 && <p className="tenue">Nothing scheduled.</p>}
        </div>
      </section>

      {done.length > 0 && (
        <section>
          <h3>Done ({done.length})</h3>
          <div className="agenda-list">
            {done.map((a) => <Row key={a.id} a={a} />)}
          </div>
        </section>
      )}
    </div>
  );
}
