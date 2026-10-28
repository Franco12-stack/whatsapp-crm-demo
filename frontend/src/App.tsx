import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { Admin } from "./pages/Admin";
import { Inbox } from "./pages/Inbox";
import { Login } from "./pages/Login";
import { SupervisorDashboard } from "./pages/SupervisorDashboard";
import { useAuth } from "./hooks/useAuth";
import { initials } from "./utils";

const NAV_ICONS: Record<string, string> = {
  "/": "💬",
  "/dashboard": "📊",
  "/admin": "⚙️",
};

function Shell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="shell">
      <aside className="sidenav">
        <div className="sidenav-brand">
          <span className="brand-mark">◆</span>
          <span className="brand-text">WhatsApp CRM</span>
        </div>

        <nav className="sidenav-links">
          <NavLink to="/" end className="sidenav-link">
            <span className="sidenav-icon">{NAV_ICONS["/"]}</span>
            Inbox
          </NavLink>
          {(user.role === "admin" || user.role === "supervisor") && (
            <NavLink to="/dashboard" className="sidenav-link">
              <span className="sidenav-icon">{NAV_ICONS["/dashboard"]}</span>
              Dashboard
            </NavLink>
          )}
          {user.role === "admin" && (
            <NavLink to="/admin" className="sidenav-link">
              <span className="sidenav-icon">{NAV_ICONS["/admin"]}</span>
              Admin
            </NavLink>
          )}
        </nav>

        <div className="sidenav-spacer" />

        <div className="sidenav-user">
          <span className="avatar">{initials(user.full_name)}</span>
          <div className="sidenav-user-info">
            <strong>{user.full_name}</strong>
            <span className={`role-chip role-${user.role}`}>{user.role}</span>
          </div>
        </div>
        <button
          className="link-btn sidenav-logout"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Log out
        </button>
      </aside>

      <div className="content">
        <Routes>
          <Route path="/" element={<Inbox />} />
          <Route path="/dashboard" element={<SupervisorDashboard />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </div>
    </div>
  );
}

export function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/*" element={<Shell />} />
    </Routes>
  );
}
