import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { Admin } from "./pages/Admin";
import { Agenda } from "./pages/Agenda";
import { Broadcasts } from "./pages/Broadcasts";
import { ContactToday } from "./pages/ContactToday";
import { Goals } from "./pages/Goals";
import { Inbox } from "./pages/Inbox";
import { Login } from "./pages/Login";
import { Metrics } from "./pages/Metrics";
import { Products } from "./pages/Products";
import { Promotions } from "./pages/Promotions";
import { Reassign } from "./pages/Reassign";
import { Support } from "./pages/Support";
import { SupervisorDashboard } from "./pages/SupervisorDashboard";
import { useAuth } from "./hooks/useAuth";
import { initials } from "./utils";
import type { Role } from "./types";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  roles: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Chats", icon: "💬", roles: ["admin", "supervisor", "agent"] },
  { to: "/agenda", label: "Agenda", icon: "📅", roles: ["agent"] },
  { to: "/contact-today", label: "Contact today", icon: "🔔", roles: ["admin", "supervisor", "agent"] },
  { to: "/broadcasts", label: "Broadcasts", icon: "📣", roles: ["admin", "supervisor", "agent"] },
  { to: "/metrics", label: "My metrics", icon: "📈", roles: ["agent"] },
  { to: "/report", label: "Report", icon: "📊", roles: ["admin", "supervisor"] },
  { to: "/dashboard", label: "Dashboard", icon: "🖥️", roles: ["admin", "supervisor"] },
  { to: "/goals", label: "Goals", icon: "🎯", roles: ["admin", "supervisor", "agent"] },
  { to: "/distribute", label: "Distribute", icon: "🔀", roles: ["admin", "supervisor"] },
  { to: "/promotions", label: "Promotions", icon: "🏷️", roles: ["admin", "supervisor", "agent"] },
  { to: "/products", label: "Products", icon: "📦", roles: ["admin", "supervisor", "agent"] },
  { to: "/support", label: "Support", icon: "🛟", roles: ["admin", "supervisor", "agent"] },
  { to: "/admin", label: "Administration", icon: "⚙️", roles: ["admin"] },
];

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
          {NAV_ITEMS.filter((item) => item.roles.includes(user.role)).map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"} className="sidenav-link">
              <span className="sidenav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
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
          <Route path="/agenda" element={<Agenda />} />
          <Route path="/contact-today" element={<ContactToday />} />
          <Route path="/broadcasts" element={<Broadcasts />} />
          <Route path="/metrics" element={<Metrics scope="me" />} />
          <Route path="/report" element={<Metrics scope="team" />} />
          <Route path="/dashboard" element={<SupervisorDashboard />} />
          <Route path="/goals" element={<Goals />} />
          <Route path="/distribute" element={<Reassign />} />
          <Route path="/promotions" element={<Promotions />} />
          <Route path="/products" element={<Products />} />
          <Route path="/support" element={<Support />} />
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
