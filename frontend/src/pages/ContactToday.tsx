import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { conversations } from "../api/endpoints";
import type { ConversationOut } from "../types";
import { avatarHue, initials } from "../utils";

/** "Contactar hoy": warm conversations that have gone quiet for 2+ days -
    worth a nudge before the lead goes cold for good. */
export function ContactToday() {
  const navigate = useNavigate();
  const [list, setList] = useState<ConversationOut[]>([]);

  useEffect(() => {
    conversations.followUps().then(setList).catch(() => undefined);
  }, []);

  function daysQuiet(lastMessageAt: string): number {
    return Math.floor((Date.now() - new Date(lastMessageAt).getTime()) / (1000 * 60 * 60 * 24));
  }

  return (
    <div className="contact-today-page">
      <header className="page-header">
        <h2>Contact today</h2>
        <p className="tenue">
          Warm conversations that have gone quiet for 2+ days — worth a nudge before the lead goes cold.
        </p>
      </header>

      <div className="agenda-list">
        {list.map((c) => (
          <div key={c.id} className="agenda-row" onClick={() => navigate("/")}>
            <span className="avatar avatar-sm" style={{ background: `hsl(${avatarHue(c.contact.name)}, 45%, 32%)` }}>
              {initials(c.contact.name)}
            </span>
            <div className="agenda-row-body">
              <strong>{c.contact.name}</strong>
              <span className="tenue">{c.contact.phone_number}</span>
            </div>
            <span className="tag cold">{daysQuiet(c.last_message_at)}d quiet</span>
          </div>
        ))}
        {list.length === 0 && <p className="tenue">Nobody's gone quiet — you're all caught up.</p>}
      </div>
    </div>
  );
}
