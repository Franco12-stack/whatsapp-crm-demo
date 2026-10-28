import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ai, conversations } from "../api/endpoints";
import { ApiError } from "../api/client";
import type { CallLogOut, ConversationOut, MessageOut } from "../types";
import { avatarHue, initials, money } from "../utils";

export function Inbox() {
  const [list, setList] = useState<ConversationOut[]>([]);
  const [selected, setSelected] = useState<ConversationOut | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [calls, setCalls] = useState<CallLogOut[]>([]);
  const [draft, setDraft] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [calling, setCalling] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const threadRef = useRef<HTMLDivElement | null>(null);

  function load() {
    conversations.list().then(setList).catch(() => undefined);
  }

  useEffect(load, []);
  useEffect(() => {
    const t = setInterval(load, 8000); // picks up the background customer simulator
    return () => clearInterval(t);
  }, []);

  function loadThread() {
    if (!selected) return;
    conversations.messages(selected.id).then(setMessages).catch(() => undefined);
    conversations.calls(selected.id).then(setCalls).catch(() => undefined);
  }

  useEffect(loadThread, [selected]);

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

  async function placeCall() {
    if (!selected) return;
    setCalling(true);
    try {
      const call = await conversations.logCall(selected.id);
      setCalls((prev) => [call, ...prev]);
      const mins = Math.floor(call.duration_seconds / 60);
      const secs = call.duration_seconds % 60;
      setNotice(`Call logged — ${mins}m ${secs}s.`);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Could not log the call");
    } finally {
      setCalling(false);
    }
  }

  async function suggestReply() {
    if (!selected) return;
    setSuggesting(true);
    try {
      const { suggestion } = await ai.suggest(selected.id);
      setDraft(suggestion);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "No suggestion available yet");
    } finally {
      setSuggesting(false);
    }
  }

  return (
    <div className="inbox">
      <aside className="conversation-list">
        <div className="conversation-list-header">
          <h3>Conversations</h3>
          <Link className="link-btn" to="/broadcasts">
            Broadcast →
          </Link>
        </div>
        {list.map((c) => (
          <div
            key={c.id}
            className={`conversation-row ${selected?.id === c.id ? "active" : ""}`}
            onClick={() => setSelected(c)}
          >
            <span
              className="avatar avatar-sm"
              style={{ background: `hsl(${avatarHue(c.contact.name)}, 45%, 32%)` }}
            >
              {initials(c.contact.name)}
            </span>
            <div className="conversation-row-body">
              <div className="conversation-row-main">
                <strong>{c.contact.name}</strong>
                <span className={`tag ${c.is_warm ? "warm" : "cold"}`}>{c.is_warm ? "warm" : "cold"}</span>
              </div>
              <span className="tenue">{c.contact.phone_number}</span>
            </div>
          </div>
        ))}
        {list.length === 0 && <p className="tenue">No conversations yet.</p>}
      </aside>

      <main className="thread-panel">
        {selected ? (
          <>
            <div className="thread-header">
              <span
                className="avatar"
                style={{ background: `hsl(${avatarHue(selected.contact.name)}, 45%, 32%)` }}
              >
                {initials(selected.contact.name)}
              </span>
              <div>
                <strong>{selected.contact.name}</strong>
                <br />
                <span className="tenue">{selected.contact.phone_number}</span>
              </div>
              <span className={`tag ${selected.is_warm ? "warm" : "cold"}`}>
                {selected.is_warm ? "warm" : "cold"}
              </span>
              <button className="secondary thread-call-btn" onClick={placeCall} disabled={calling}>
                📞 {calling ? "Calling..." : "Call"}
              </button>
            </div>
            <div className="thread" ref={threadRef}>
              {messages.map((m) => (
                <div key={m.id} className={`bubble ${m.direction}`}>
                  {m.body}
                </div>
              ))}
            </div>
            <div className="composer">
              <button className="secondary ai-suggest-btn" onClick={suggestReply} disabled={suggesting}>
                ✨ {suggesting ? "Thinking..." : "Suggest reply"}
              </button>
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

      {selected && (
        <aside className="contact-panel">
          <div className="contact-panel-head">
            <span
              className="avatar"
              style={{ background: `hsl(${avatarHue(selected.contact.name)}, 45%, 32%)` }}
            >
              {initials(selected.contact.name)}
            </span>
            <strong>{selected.contact.name}</strong>
            <span className="tenue">{selected.contact.phone_number}</span>
          </div>

          <div className="contact-panel-section">
            <h4>CRM</h4>
            <dl className="kv">
              <dt>Account</dt>
              <dd>{selected.contact.crm_account ?? "—"}</dd>
              <dt>Lifetime value</dt>
              <dd>{money(selected.contact.lifetime_value)}</dd>
              <dt>Last order</dt>
              <dd>
                {selected.contact.last_order_at
                  ? new Date(selected.contact.last_order_at).toLocaleDateString()
                  : "No orders yet"}
              </dd>
            </dl>
            <p className="tenue sync-note">Synced from the connected CRM (simulated for this demo).</p>
          </div>

          <div className="contact-panel-section">
            <h4>Calls ({calls.length})</h4>
            {calls.length === 0 && <p className="tenue">No calls logged yet.</p>}
            <ul className="call-list">
              {calls.map((c) => (
                <li key={c.id}>
                  <span>📞 {Math.floor(c.duration_seconds / 60)}m {c.duration_seconds % 60}s</span>
                  <span className="tenue">{new Date(c.created_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      )}
    </div>
  );
}
