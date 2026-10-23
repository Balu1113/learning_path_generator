import { useState, useEffect } from "react";
import { getStats, getDeadlineAlerts } from "../api/client";
import { useAuth } from "../auth";
import { BarChart3, Loader2, TriangleAlert } from "lucide-react";

const ALERT_LABELS = {
  overdue: "Overdue",
  critical: "Critical",
  behind: "Behind pace",
};

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [alerts, setAlerts] = useState(null);

  useEffect(() => {
    getStats()
      .then((d) => {
        if (d.error) setError(d.error);
        else setStats(d);
      })
      .catch(() => setError("Failed to load stats"));
  }, []);

  useEffect(() => {
    if (!user) {
      setAlerts(null);
      return;
    }
    getDeadlineAlerts()
      .then((d) => {
        if (!d.error) setAlerts(d.alerts || []);
      })
      .catch(() => {});
  }, [user]);

  if (error) {
    return (
      <div className="page-container">
        <div className="error-box">{error}</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Loading stats...</p>
        </div>
      </div>
    );
  }

  const maxDay = Math.max(1, ...stats.by_day.map((d) => d.count));

  return (
    <div className="page-container">
      <div className="page-header">
        <BarChart3 size={28} />
        <div>
          <h2>Usage Dashboard</h2>
          <p className="subtitle">Overview of generated learning paths.</p>
        </div>
      </div>

      <div className="stat-cards">
        <div className="stat-card"><span className="stat-num">{stats.total_paths}</span><span className="stat-label">Paths generated</span></div>
        <div className="stat-card"><span className="stat-num">{stats.total_users}</span><span className="stat-label">Users</span></div>
        <div className="stat-card"><span className="stat-num">{stats.feedback.up}</span><span className="stat-label">Thumbs up</span></div>
        <div className="stat-card"><span className="stat-num">{stats.feedback.down}</span><span className="stat-label">Thumbs down</span></div>
        <div className="stat-card"><span className="stat-num">{stats.by_source.quick || 0}</span><span className="stat-label">Quick Path</span></div>
        <div className="stat-card"><span className="stat-num">{stats.by_source.agent || 0}</span><span className="stat-label">Agent Mode</span></div>
      </div>

      {user && alerts && alerts.length > 0 && (
        <div className="help-section deadline-alerts">
          <h3><TriangleAlert size={16} /> Deadline risk</h3>
          <div className="topics-list">
            {alerts.map((a) => (
              <div key={a.path_id} className={`topic-item deadline-alert status-${a.status}`}>
                <div className="deadline-alert-head">
                  <span className={`deadline-chip ${a.status}`}>{ALERT_LABELS[a.status] || a.status}</span>
                  <strong>{a.goal}</strong>
                </div>
                <p className="topic-resources">
                  {a.days_left < 0
                    ? `${-a.days_left} day${a.days_left === -1 ? "" : "s"} overdue · `
                    : `${a.days_left} day${a.days_left === 1 ? "" : "s"} left · `}
                  target {a.target_date} · {a.actual_pct}% done, expected {a.expected_pct}%
                  {a.behind > 0 ? ` (${a.behind} behind)` : ""}
                </p>
                <div className="progress-bar-wrap">
                  <div className="progress-bar" style={{ width: `${a.actual_pct}%` }} />
                  <span className="progress-label">actual {a.actual_pct}% / expected {a.expected_pct}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="help-section">
        <h3>Generations — last 14 days</h3>
        <div className="bar-chart">
          {stats.by_day.map((d) => (
            <div key={d.date} className="bar-col" title={`${d.date}: ${d.count}`}>
              <div className="bar" style={{ height: `${(d.count / maxDay) * 100}%` }} />
              <span className="bar-count">{d.count}</span>
              <span className="bar-date">{d.date.slice(5)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="help-section">
        <h3>Top goals</h3>
        <div className="topics-list">
          {stats.top_goals.map((g, i) => (
            <div key={i} className="topic-item">
              <strong>{g.goal}</strong>
              <p className="topic-resources">{g.count} generation{g.count === 1 ? "" : "s"}</p>
            </div>
          ))}
          {stats.top_goals.length === 0 && <p className="subtitle">No goals yet.</p>}
        </div>
      </div>
    </div>
  );
}
