import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "../api/endpoints";
import { ApiError } from "../api/client";
import { useAuth } from "../hooks/useAuth";

const DEMO_ACCOUNTS = [
  { label: "Admin", email: "admin@demo.com" },
  { label: "Supervisor", email: "supervisor@demo.com" },
  { label: "Agent (just-connected line)", email: "nicole@demo.com" },
  { label: "Agent (warming up)", email: "marcus@demo.com" },
  { label: "Agent (fully warmed up)", email: "priya@demo.com" },
];

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@demo.com");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const result = await auth.login(email, password);
      login(result.access_token, result.user);
      navigate("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not log in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>WhatsApp CRM Demo</h1>
        <p className="subtitle">A multichannel sales inbox with anti-ban rate limiting built in.</p>

        <label className="field">
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>

        {error && <div className="notice error">{error}</div>}

        <button onClick={submit} disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>

        <div className="demo-accounts">
          <p className="tenue">Quick demo accounts (password: demo1234):</p>
          {DEMO_ACCOUNTS.map((acc) => (
            <button
              key={acc.email}
              className="demo-account-chip"
              onClick={() => {
                setEmail(acc.email);
                setPassword("demo1234");
              }}
            >
              {acc.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
