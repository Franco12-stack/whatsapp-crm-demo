import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { Admin } from "./pages/Admin";
import { Inbox } from "./pages/Inbox";
import { Login } from "./pages/Login";
import { SupervisorDashboard } from "./pages/SupervisorDashboard";
import { useAuth } from "./hooks/useAuth";

function Shell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="shell">
      <nav className="topnav">
        <span className="brand">WhatsApp CRM Demo</span>
        <NavLink to="/" end>
          Inbox
        </NavLink>
        {(user.role === "admin" || user.role === "supervisor") && (
          <NavLink to="/dashboard">Dashboard</NavLink>
        )}
        {user.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
        <span className="spacer" />
        <span className="tenue">
          {user.full_name} ({user.role})
        </span>
        <button
          className="link-btn"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Log out
        </button>
      </nav>
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
