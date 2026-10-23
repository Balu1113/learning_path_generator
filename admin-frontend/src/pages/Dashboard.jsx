import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Users,
  MessageSquare,
  CircleCheck,
  Layers,
  Activity,
  FileCheck,
  Award,
  Map,
} from "lucide-react";
import { fetchCounts } from "../api.js";

const CARDS = [
  { key: "users", label: "Users", to: "/r/users", icon: Users },
  { key: "feedback", label: "Feedback", to: "/r/feedback", icon: MessageSquare },
  { key: "progress", label: "Progress", to: "/r/progress", icon: CircleCheck },
  { key: "flashcards", label: "Flashcards", to: "/r/flashcards", icon: Layers },
  { key: "activity", label: "Activity", to: "/r/activity", icon: Activity },
  { key: "tests", label: "Test results", to: "/r/tests", icon: FileCheck },
  { key: "badges", label: "Badges", to: "/r/badges", icon: Award },
  { key: "paths", label: "Paths", to: "/r/paths", icon: Map },
];

export default function Dashboard() {
  const [counts, setCounts] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCounts()
      .then(setCounts)
      .catch((e) => setError(e.message || "Failed to load counts"));
  }, []);

  return (
    <div>
      <header className="page-head">
        <h2>Dashboard</h2>
        <div className="chips">
          {counts && (
            <>
              <span className="chip">{counts.active_users} active users</span>
              <span className="chip">{counts.superusers} superusers</span>
              <span className="chip warn">{counts.due_flashcards} cards due</span>
            </>
          )}
        </div>
      </header>
      {error && <div className="banner error">{error}</div>}
      {!counts && !error && <p className="muted">Loading counts…</p>}
      {counts && (
        <div className="card-grid">
          {CARDS.map(({ key, label, to, icon: Icon }) => (
            <Link key={key} to={to} className="stat-card">
              <span className="stat-icon">
                <Icon size={18} />
              </span>
              <span className="stat-value">{counts[key]}</span>
              <span className="stat-label">{label}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
