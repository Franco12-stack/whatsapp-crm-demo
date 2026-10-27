import { useEffect, useRef, useState } from "react";
import { broadcasts, conversations } from "../api/endpoints";
import { ApiError } from "../api/client";
import type { ConversationOut, MessageOut } from "../types";

export function Inbox() {
  const [list, setList] = useState<ConversationOut[]>([]);
  const [selected, setSelected] = useState<ConversationOut | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [draft, setDraft] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [broadcastMode, setBroadcastMode] = useState(false);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const threadRef = useRef<HTMLDivElement | null>(null);

  function load() {
    conversations.list().then(setList).catch(() => undefined);
  }

  useEffect(load, []);
  useEffect(() => {
    const t = setInterval(load, 8000); // picks up the background customer simulator
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!selected) return;
    conversations.messages(selected.id).then(setMessages).catch(() => undefined);
  }, [selected]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [messages]);

  async function send() {
    if (!selected || !draft.trim()) return;
    try {
      const msg = await conversations.send(selected.id, draft.trim());
      setMessages((prev) => [...prev, msg]);
      setDraft("");
      load();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Could not send");
    }
  }

  function toggleCheck(id: string) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function sendBroadcast(force: boolean) {
    if (checked.size === 0 || !draft.trim()) return;
    try {
      const result = await broadcasts.send(Array.from(checked), draft.trim(), force);
      if (result.skipped_cold.length > 0 && !force) {
        setNotice(
          `Sent to ${result.sent_to.length}. Skipped ${result.skipped_cold.length} cold contact(s): ` +
            result.skipped_cold.map((c) => c.contact_name).join(", ") +
            `. Use "Send to everyone anyway" to override.`,
        );
      } else {
        setNotice(`Sent to ${result.sent_to.length} conversation(s).`);
      }
      setDraft("");
      setChecked(new Set());
      load();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Could not send broadcast");
    }
  }

  return (
    <div className="inbox">
      <aside className="conversation-list">
        <div className="conversation-list-header">
          <h3>Conversations</h3>
          <button className="link-btn" onClick={() => setBroadcastMode((v) => !v)}>
            {broadcastMode ? "Cancel broadcast" : "Broadcast"}
          </button>
        </div>
        {list.map((c) => (
          <div
            key={c.id}
            className={`conversation-row ${selected?.id === c.id ? "active" : ""}`}
            onClick={() => (broadcastMode ? toggleCheck(c.id) : setSelected(c))}
          >
            {broadcastMode && (
              <input type="checkbox" checked={checked.has(c.id)} onChange={() => toggleCheck(c.id)} />
            )}
            <div className="conversation-row-main">
              <strong>{c.contact.name}</strong>
              <span className={`tag ${c.is_warm ? "warm" : "cold"}`}>{c.is_warm ? "warm" : "cold"}</span>
            </div>
            <span className="tenue">{c.contact.phone_number}</span>
          </div>
        ))}
        {list.length === 0 && <p className="tenue">No conversations yet.</p>}
      </aside>

      <main className="thread-panel">
        {broadcastMode ? (
          <div className="broadcast-panel">
            <h3>Broadcast ({checked.size} selected)</h3>
            <p className="tenue">
              Cold contacts (no prior reply) are skipped by default - opening many cold
              conversations at once is the clearest spam signal there is.
            </p>
            <textarea
              rows={4}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Broadcast message..."
            />
            <div className="actions">
              <button onClick={() => sendBroadcast(false)}>Send (skip cold)</button>
              <button className="secondary" onClick={() => sendBroadcast(true)}>
                Send to everyone anyway
              </button>
            </div>
          </div>
        ) : selected ? (
          <>
            <div className="thread-header">
              <strong>{selected.contact.name}</strong>
              <span className="tenue">{selected.contact.phone_number}</span>
            </div>
            <div className="thread" ref={threadRef}>
              {messages.map((m) => (
                <div key={m.id} className={`bubble ${m.direction}`}>
                  {m.body}
                </div>
              ))}
            </div>
            <div className="composer">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Type a message..."
              />
              <button onClick={send}>Send</button>
            </div>
          </>
        ) : (
          <p className="tenue centered">Select a conversation to start.</p>
        )}

        {notice && (
          <div className="notice" onClick={() => setNotice(null)}>
            {notice}
          </div>
        )}
      </main>
    </div>
  );
}
