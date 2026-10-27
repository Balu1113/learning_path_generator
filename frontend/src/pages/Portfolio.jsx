import { useEffect, useState } from "react";
import { getPortfolio, exportPortfolio, updatePortfolioPrivacy } from "../api/client";
import { useAuth } from "../auth";
import { Download, Globe, Loader2, Lock, Settings, Share2, Shield, User } from "lucide-react";

export default function Portfolio() {
  const { user } = useAuth();
  const [passport, setPassport] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    if (!user) return;
    getPortfolio()
      .then((d) => {
        if (d.error) setError(d.error);
        else {
          setPassport(d.passport);
          setSettings(d.settings);
        }
      })
      .catch(() => setError("Failed to load your portfolio."))
      .finally(() => setLoading(false));
  }, [user]);

  const handleExport = async () => {
    try {
      const blob = await exportPortfolio();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `skill-passport-${user?.username || "user"}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed.");
    }
  };

  const togglePrivacy = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const d = await updatePortfolioPrivacy({ ...settings, is_public: !settings.is_public });
      if (d.error) setError(d.error);
      else setSettings(d.settings);
    } catch {
      setError("Failed to update privacy settings.");
    }
    setSaving(false);
  };

  if (!user) {
    return (
      <div className="page-container">
        <div className="page-header">
          <User size={28} />
          <div>
            <h2>Skill Passport</h2>
            <p className="subtitle">Your evidence-based learning portfolio.</p>
          </div>
        </div>
        <div className="empty-state">
          <Lock size={48} />
          <p>Log in to view and manage your Skill Passport.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Loading your portfolio...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="page-container"><div className="error-box">{error}</div></div>;
  }

  if (!passport) return null;

  return (
    <div className="page-container">
      <div className="page-header">
        <User size={28} />
        <div>
          <h2>Skill Passport</h2>
          <p className="subtitle">Evidence-based portfolio of your validated skills and shipped projects.</p>
        </div>
        <div className="page-actions">
          <button className="btn-secondary" onClick={() => setShowSettings(true)}>
            <Settings size={16} /> Privacy
          </button>
          <button className="btn-primary" onClick={handleExport}>
            <Download size={16} /> Export Markdown
          </button>
        </div>
      </div>

      {settings?.is_public && (
        <div className="saved-note">
          <Globe size={14} /> Your portfolio is public at <code>/portfolio/{user.username}</code>
        </div>
      )}

      <div className="portfolio-stats">
        <div className="stat-card">
          <span className="stat-num">{passport.validated_count}</span>
          <span className="stat-label">Validated Skills</span>
        </div>
        <div className="stat-card">
          <span className="stat-num">{passport.developing_count}</span>
          <span className="stat-label">Developing</span>
        </div>
        {passport.study_hours !== null && (
          <div className="stat-card">
            <span className="stat-num">{passport.study_hours}h</span>
            <span className="stat-label">Study Time</span>
          </div>
        )}
        <div className="stat-card">
          <span className="stat-num">{passport.projects.length}</span>
          <span className="stat-label">Projects Shipped</span>
        </div>
      </div>

      <div className="help-section">
        <h3>Validated Skills</h3>
        {passport.skills.filter((s) => s.state === "validated").length === 0 ? (
          <p className="subtitle">No validated skills yet. Pass phase tests and get projects reviewed.</p>
        ) : (
          <div className="skills-grid">
            {passport.skills.filter((s) => s.state === "validated").map((s) => (
              <div key={s.slug} className="skill-badge validated">
                <strong>{s.name}</strong>
                <span>{s.domain}</span>
                <small>best score {s.score}%</small>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="help-section">
        <h3>Developing Skills</h3>
        {passport.skills.filter((s) => s.state === "developing").length === 0 ? (
          <p className="subtitle">No developing skills yet.</p>
        ) : (
          <div className="skills-grid">
            {passport.skills.filter((s) => s.state === "developing").map((s) => (
              <div key={s.slug} className="skill-badge developing">
                <strong>{s.name}</strong>
                <span>{s.domain}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {settings?.show_projects && passport.projects.length > 0 && (
        <div className="help-section">
          <h3>Shipped Projects</h3>
          <div className="topics-list">
            {passport.projects.map((p, i) => (
              <div key={i} className="topic-item">
                <div className="topic-head">
                  <strong>{p.title}</strong>
                  <span className="topic-meta">{p.phase_title} · score {p.score}/100</span>
                </div>
                {p.submission_url && (
                  <a href={p.submission_url} target="_blank" rel="noreferrer" className="topic-link">
                    <Share2 size={12} /> {p.submission_url}
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {settings?.show_test_scores && passport.test_results.length > 0 && (
        <div className="help-section">
          <h3>Recent Phase Tests</h3>
          <div className="topics-list">
            {passport.test_results.map((r, i) => (
              <div key={i} className="topic-item">
                <strong>{r.phase_title}</strong>
                <span className="topic-meta">{r.date} · {r.percent}% ({r.score}/{r.total})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3><Shield size={18} /> Portfolio Privacy</h3>
              <button className="modal-close" onClick={() => setShowSettings(false)}>×</button>
            </div>
            <div className="modal-body">
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={settings.is_public}
                  onChange={togglePrivacy}
                  disabled={saving}
                />
                <span>Make my portfolio public</span>
                {settings.is_public ? <Globe size={14} /> : <Lock size={14} />}
              </label>
              <p className="subtitle">
                When public, anyone can view your Skill Passport at <code>/portfolio/{user.username}</code>.
                It shows validated skills, shipped projects, and test scores.
              </p>
              <hr />
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={settings.show_projects}
                  onChange={() => setSettings((s) => ({ ...s, show_projects: !s.show_projects }))}
                />
                <span>Show projects</span>
              </label>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={settings.show_test_scores}
                  onChange={() => setSettings((s) => ({ ...s, show_test_scores: !s.show_test_scores }))}
                />
                <span>Show test scores</span>
              </label>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={settings.show_study_hours}
                  onChange={() => setSettings((s) => ({ ...s, show_study_hours: !s.show_study_hours }))}
                />
                <span>Show study hours</span>
              </label>
              <button
                className="btn-primary"
                onClick={async () => {
                  setSaving(true);
                  const d = await updatePortfolioPrivacy(settings);
                  if (d.error) setError(d.error);
                  else setSettings(d.settings);
                  setSaving(false);
                  setShowSettings(false);
                }}
                disabled={saving}
              >
                {saving ? <Loader2 className="spin" size={16} /> : "Save Settings"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}