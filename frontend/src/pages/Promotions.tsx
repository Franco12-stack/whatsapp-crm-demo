import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { promotions } from "../api/endpoints";
import { useAuth } from "../hooks/useAuth";
import type { PromotionOut } from "../types";

export function Promotions() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";
  const [list, setList] = useState<PromotionOut[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  function load() {
    promotions.list().then(setList).catch(() => undefined);
  }

  useEffect(load, []);

  async function create() {
    if (!title.trim() || !body.trim()) return;
    await promotions.create(title.trim(), body.trim());
    setTitle("");
    setBody("");
    load();
  }

  return (
    <div className="promotions-page">
      <header className="page-header">
        <h2>Promotions</h2>
        <p className="tenue">Reusable templates — pick one to prefill a broadcast.</p>
      </header>

      {isAdmin && (
        <section className="support-form">
          <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <textarea rows={2} placeholder="Message body" value={body} onChange={(e) => setBody(e.target.value)} />
          <button onClick={create}>Add promotion</button>
        </section>
      )}

      <div className="promo-cards">
        {list.map((p) => (
          <div key={p.id} className="agent-card">
            <div className="agent-card-head" style={{ marginBottom: 8 }}>
              <strong>{p.title}</strong>
              {!p.active && <span className="tag cold">inactive</span>}
            </div>
            <p className="tenue">{p.body}</p>
            <button className="secondary" onClick={() => navigate("/broadcasts", { state: { prefill: p.body } })}>
              Use in broadcast
            </button>
          </div>
        ))}
        {list.length === 0 && <p className="tenue">No promotions yet.</p>}
      </div>
    </div>
  );
}
