import { useEffect, useState } from "react";
import { extractSkills, getSkillMatrix } from "../api/client";
import { AlertTriangle, CheckCircle2, Circle, Loader2, Sparkles, TrendingUp } from "lucide-react";

const STATE_META = {
  validated: { label: "Validated", icon: CheckCircle2, cls: "validated" },
  developing: { label: "Developing", icon: TrendingUp, cls: "developing" },
  unassessed: { label: "Unassessed", icon: Circle, cls: "unassessed" },
};

export default function SkillsMatrix({ pathId }) {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!pathId) return undefined;
    let alive = true;
    setLoading(true);
    getSkillMatrix(pathId)
      .then((d) => alive && !d.error && setMatrix(d))
      .catch(() => alive && setError("Failed to load the skill matrix."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [pathId]);

  const runExtract = async () => {
    setExtracting(true);
    setError("");
    try {
      const d = await extractSkills(pathId);
      if (d.error) setError(d.error);
      else setMatrix(d.matrix);
    } catch {
      setError("Failed to extract skills.");
    }
    setExtracting(false);
  };

  if (loading) {
    return (
      <div className="empty-state small">
        <Loader2 className="spin" size={22} />
        <p>Loading skill matrix...</p>
      </div>
    );
  }

  const skills = matrix?.skills || [];
  const counts = matrix?.counts || { unassessed: 0, developing: 0, validated: 0 };
  const nameBySlug = Object.fromEntries(skills.map((s) => [s.slug, s.name]));

  return (
    <div className="skills-matrix">
      {error && <div className="error-box">{error}</div>}

      {skills.length === 0 ? (
        <div className="study-empty">
          <span className="study-empty-icon"><Sparkles size={26} /></span>
          <strong>No skill graph yet</strong>
          <p>
            Extract the durable skills from this roadmap, their prerequisites, and how
            each topic maps to them. Mastery updates automatically from phase tests and
            project reviews.
          </p>
          <button className="btn-primary" onClick={runExtract} disabled={extracting}>
            {extracting ? <Loader2 className="spin" size={15} /> : <Sparkles size={15} />}
            Extract skills
          </button>
        </div>
      ) : (
        <>
          <div className="skills-counts">
            {["validated", "developing", "unassessed"].map((state) => {
              const meta = STATE_META[state];
              const Icon = meta.icon;
              return (
                <span key={state} className={`skills-count chips-${meta.cls}`}>
                  <Icon size={13} /> {counts[state] ?? 0} {meta.label.toLowerCase()}
                </span>
              );
            })}
            <button className="ws-chip-btn" onClick={runExtract} disabled={extracting} title="Re-extract the skill graph">
              {extracting ? <Loader2 className="spin" size={13} /> : <Sparkles size={13} />} Re-extract
            </button>
          </div>

          <ul className="skills-list">
            {skills.map((s) => {
              const meta = STATE_META[s.state] || STATE_META.unassessed;
              const Icon = meta.icon;
              return (
                <li key={s.slug} className={`skills-item ${meta.cls}`}>
                  <span className="skills-state" title={meta.label}>
                    <Icon size={14} />
                  </span>
                  <div className="skills-body">
                    <strong>{s.name}</strong>
                    {s.description && <em>{s.description}</em>}
                    <small>
                      {s.domain && <span className="skills-domain">{s.domain}</span>}
                      {s.score != null && <span>best score {s.score}%</span>}
                      {s.evidence_count > 0 && (
                        <span>{s.evidence_count} evidence</span>
                      )}
                    </small>
                  </div>
                </li>
              );
            })}
          </ul>

          {matrix.edges?.length > 0 && (
            <div className="skills-edges">
              <strong>Prerequisites</strong>
              <ul>
                {matrix.edges.map((e, i) => (
                  <li key={i}>
                    {nameBySlug[e.from] || e.from} <span aria-hidden="true">→</span>{" "}
                    {nameBySlug[e.to] || e.to}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {counts.unassessed > 0 && (
            <p className="skills-hint">
              <AlertTriangle size={13} /> Unassessed skills gain evidence when you pass
              phase checks or get projects reviewed.
            </p>
          )}
        </>
      )}
    </div>
  );
}
