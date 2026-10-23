import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  CircleCheck,
  Layers,
  Activity,
  FileCheck,
  Award,
  Map,
  LogOut,
} from "lucide-react";
import { logout } from "../api.js";
import { useAuth } from "../context.jsx";

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard", end: true },
  { to: "/r/users", icon: Users, label: "Users" },
  { to: "/r/feedback", icon: MessageSquare, label: "Feedback" },
  { to: "/r/progress", icon: CircleCheck, label: "Progress" },
  { to: "/r/flashcards", icon: Layers, label: "Flashcards" },
  { to: "/r/activity", icon: Activity, label: "Activity" },
  { to: "/r/tests", icon: FileCheck, label: "Tests" },
  { to: "/r/badges", icon: Award, label: "Badges" },
  { to: "/r/paths", icon: Map, label: "Paths" },
];

export default function Layout() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();

  const signOut = async () => {
    await logout().catch(() => {});
    setUser(null);
    navigate("/login", { replace: true });
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <ShieldMark />
          <span>LearnPath Admin</span>
        </div>
        <nav>
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="who">{user?.username}</span>
          <button className="btn subtle" onClick={signOut}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

function ShieldMark() {
  return (
    <span className="brand-mark">
      <Layers size={15} />
    </span>
  );
}
