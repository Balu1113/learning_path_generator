import { useState } from "react";
import { analyzeJobTarget, getSkillMatrix } from "../api/client";
import { useAuth } from "../auth";
import { AlertTriangle, Briefcase, Loader2, Target, Zap } from "lucide-react";

export default function JobTarget() {
  const { user } = useAuth();
  const [jd, setJd] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const d = await analyzeJobTarget(jd);
      if (d.error) setError(d.error);
      else setResult(d);
    } catch {
      setError("Analysis failed.");
    }
    setLoading(false);
  };

  if (!user) {
    return (
      <div className="page-container">
        <div className="page-header">
          <Briefcase size={28} />
          <div>
            <h2>Job-Target Mode</h2>
            <p className="subtitle">Paste a job description to see skill gaps and a learning plan.</p>
          </div>
        </div>
        <div className="empty-state">
          <Target size={48} />
          <p>Log in to analyze job descriptions against your skill matrix.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Briefcase size={28} />
        <div>
          <h2>Job-Target Mode</h2>
          <p className="subtitle">Paste a job description to see skill gaps and a learning plan.</p>
        </div>
      </div>

      <div className="help-section">
        <h3><Target size={16} /> Job Description</h3>
        <textarea
          rows={8}
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          placeholder="Paste the full job description here..."
        />
        <button className="btn-primary" onClick={run} disabled={loading || !jd.trim()}>
          {loading ? <Loader2 className="spin" size={16} /> : <Zap size={16} />} Analyze Gaps
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {result && (
        <div className="help-section">
          <h3>{result.role_title || "Analysis Results"}</h3>
          <p className="subtitle">{result.gap_summary}</p>

          <div className="job-stats">
            <div className="stat-card">
              <span className="stat-num">{result.ready_count}</span>
              <span className="stat-label">Skills Ready</span>
            </div>
            <div className="stat-card alert">
              <span className="stat-num">{result.gap_count}</span>
              <span className="stat-label">Gaps</span>
            </div>
          </div>

          <h4>Required Skills</h4>
          <div className="skills-table">
            <table>
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Importance</th>
                  <th>Your State</th>
                  <th>Why it matters</th>
                </tr>
              </thead>
              <tbody>
                {result.required_skills?.map((s, i) => (
                  <tr key={i} className={s.learner_state === "validated" ? "ready" : "gap"}>
                    <td><strong>{s.name}</strong></td>
                    <td><span className={`importance-badge ${s.importance}`}>{s.importance}</span></td>
                    <td>
                      {s.learner_state === "validated" ? "✅ Validated" :
                       s.learner_state === "developing" ? "🔄 Developing" : "❌ Unassessed"}
                    </td>
                    <td>{s.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.gap_skills?.length > 0 && (
            <div className="job-hint">
              <AlertTriangle size={16} />
              <p><strong>Focus first:</strong> {result.gap_path_hint}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}