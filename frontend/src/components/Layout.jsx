import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Brain, Zap, Layers, History, BarChart3, HelpCircle, GraduationCap, LogIn, LogOut, BookOpen, Sun, Moon, ShieldCheck, Library, Users, FolderSearch } from "lucide-react";
import { useAuth } from "../auth";
import { logoutUser } from "../api/client";
import { useTheme } from "../theme";
import "./Layout.css";

const NAV_ITEMS = [
  { to: "/", icon: Brain, label: "Agent Mode" },
  { to: "/quick", icon: Zap, label: "Quick Path" },
  { to: "/domains", icon: Layers, label: "Domains" },
  { to: "/resources", icon: FolderSearch, label: "Resources" },
  { to: "/gallery", icon: Library, label: "Gallery" },
  { to: "/study", icon: BookOpen, label: "Study" },
  { to: "/groups", icon: Users, label: "Groups" },
  { to: "/history", icon: History, label: "Path History" },
  { to: "/dashboard", icon: BarChart3, label: "Dashboard" },
  { to: "/help", icon: HelpCircle, label: "Help" },
];

export default function Layout() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleLogout = async () => {
    await logoutUser().catch(() => {});
    setUser(null);
    navigate("/");
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="logo">
          <GraduationCap size={32} />
          <span>LearnPath</span>
        </div>
        <nav>
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`} end={to === "/"} title={label} aria-label={label}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button
            className="btn-icon theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
          >
            {theme === "light" ? <Moon size={14} /> : <Sun size={14} />}
            <span>{theme === "light" ? "Dark" : "Light"}</span>
          </button>
          {user?.is_superuser && (
            <a className="btn-icon admin-link" href="/admin/" target="_blank" rel="noopener noreferrer" title="Open Django admin">
              <ShieldCheck size={14} /> Admin
            </a>
          )}
          {user ? (
            <div className="user-area">
              <span className="user-name">{user.username}</span>
              <button className="btn-icon" onClick={handleLogout} title="Log out">
                <LogOut size={14} /> Log out
              </button>
            </div>
          ) : (
            <NavLink to="/login" className="btn-icon login-link">
              <LogIn size={14} /> Log in
            </NavLink>
          )}
          <span>Powered by Gemini + LangChain</span>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
