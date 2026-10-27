import { useEffect, useState } from "react";
import {
  generateProject,
  getProject,
  reviewProject,
  submitProject,
} from "../api/client";
import {
  CheckCircle2,
  ExternalLink,
  FolderGit2,
  Loader2,
  Rocket,
  Send,
  Sparkles,
  XCircle,
} from "lucide-react";

const STATUS_LABELS = {
  draft: "Not started",
  in_progress: "In progress",
  submitted: "Awaiting review",
  reviewed: "Reviewed",
};

function RubricTable({ rubric, score }) {
  const total = rubric.reduce((a, r) => a + (r.max_points || 0), 0);
  return (
    <table className="ws-rubric">
      <thead>
        <tr>
          <th>Criterion</th>
          <th>Points</th>
        </tr>
      </thead>
      <tbody>
        {rubric.map((r, i) => (
          <tr key={i}>
            <td>
              <strong>{r.criterion}</strong>
              {r.description && <em>{r.description}</em>}
            </td>
            <td>{r.max_points}</td>
          </tr>
        ))}
        <tr className="ws-rubric-total">
          <td>Total{score != null ? " (your score)" : ""}</td>
          <td>{score != null ? `${score}/${total || 100}` : total || 100}</td>
        </tr>
      </tbody>
    </table>
  );
}

export default function PhaseProject({ pathId, phaseIdx, phaseTitle }) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showTemplate, setShowTemplate] = useState(false);
  const [url, setUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [reviewMeta, setReviewMeta] = useState(null);

  useEffect(() => {
    setProject(null);
    setReviewMeta(null);
    setError("");
    setUrl("");
    setNotes("");
    setShowTemplate(false);
    if (phaseIdx == null || !pathId) return undefined;
    let alive = true;
    setLoading(true);
    getProject(pathId, phaseIdx)
      .then((d) => {
        if (!alive) return;
        if (d.error) {
          setProject(null);
        } else {
          setProject(d.project);
          setUrl(d.project.submission_url || "");
          setNotes(d.project.submission_notes || "");
        }
      })
      .catch(() => alive && setError("Failed to load the project."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [pathId, phaseIdx]);

  const generate = async () => {
    setBusy(true);
    setError("");
    try {
      const d = await generateProject(pathId, { phase_idx: phaseIdx });
      if (d.error) setError(d.error);
      else if (d.projects?.length) {
        setProject(d.projects[0]);
        setUrl(d.projects[0].submission_url || "");
        setNotes(d.projects[0].submission_notes || "");
      }
    } catch {
      setError("Failed to generate the project.");
    }
    setBusy(false);
  };

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const d = await submitProject(pathId, phaseIdx, {
        submission_url: url.trim(),
        submission_notes: notes.trim(),
      });
      if (d.error) setError(d.error);
      else {
        setProject(d.project);
        setReviewMeta(null);
      }
    } catch {
      setError("Failed to submit the project.");
    }
    setBusy(false);
  };

  const review = async () => {
    setBusy(true);
    setError("");
    try {
      const d = await reviewProject(pathId, phaseIdx);
      if (d.error) setError(d.error);
      else {
        setProject(d.project);
        setReviewMeta({ criteria_met: d.criteria_met, criteria_missed: d.criteria_missed });
      }
    } catch {
      setError("Failed to review the project.");
    }
    setBusy(false);
  };

  if (phaseIdx == null) return null;

  return (
    <section className="study-card ws-project-card" id="phase-project">
      <div className="study-card-head">
        <div>
          <div className="study-card-title">
            <Rocket size={17} /> Capstone project{phaseTitle ? ` · ${phaseTitle}` : ""}
          </div>
          <div className="study-card-sub">
            Ship a real deliverable to turn this phase into portfolio evidence.
          </div>
        </div>
        {project && (
          <span className={`ws-project-status status-${project.status}`}>
            {STATUS_LABELS[project.status] || project.status}
          </span>
        )}
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="study-card-body">
        {loading ? (
          <div className="empty-state small">
            <Loader2 className="spin" size={22} />
            <p>Loading project...</p>
          </div>
        ) : !project ? (
          <div className="ws-project-empty">
            <p>
              No project for this phase yet. Generate a scoped capstone with a brief,
              acceptance criteria, a starter template, and a grading rubric.
            </p>
            <button className="btn-primary" onClick={generate} disabled={busy}>
              {busy ? <Loader2 className="spin" size={15} /> : <Sparkles size={15} />}
              Generate project
            </button>
          </div>
        ) : (
          <div className="ws-project">
            <h4 className="ws-project-title">{project.title}</h4>
            <p className="ws-project-brief">{project.brief}</p>

            {project.acceptance_criteria?.length > 0 && (
              <div className="ws-project-block">
                <strong>Acceptance criteria</strong>
                <ul className="ws-criteria">
                  {project.acceptance_criteria.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {project.starter_template && (
              <div className="ws-project-block">
                <button
                  className="ws-project-toggle"
                  onClick={() => setShowTemplate((v) => !v)}
                >
                  <FolderGit2 size={14} />
                  {showTemplate ? "Hide starter template" : "Show starter template"}
                </button>
                {showTemplate && (
                  <pre className="ws-starter">{project.starter_template}</pre>
                )}
              </div>
            )}

            {project.rubric?.length > 0 && (
              <div className="ws-project-block">
                <strong>Rubric</strong>
                <RubricTable rubric={project.rubric} score={project.ai_score} />
              </div>
            )}

            <div className="ws-project-block">
              <strong>Submission</strong>
              {project.status === "reviewed" ? (
                <div className="ws-submission-summary">
                  {project.submission_url && (
                    <a href={project.submission_url} target="_blank" rel="noreferrer">
                      <ExternalLink size={14} /> {project.submission_url}
                    </a>
                  )}
                  {project.submission_notes && <p>{project.submission_notes}</p>}
                </div>
              ) : (
                <div className="ws-submit-form">
                  <input
                    type="url"
                    placeholder="https://github.com/you/project"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                  <textarea
                    placeholder="What did you build? How do reviewers verify each criterion? Paste key files, commands, or outputs."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                  />
                  <button
                    className="btn-primary"
                    onClick={submit}
                    disabled={busy || (!url.trim() && !notes.trim())}
                  >
                    {busy ? <Loader2 className="spin" size={15} /> : <Send size={15} />}
                    {project.status === "reviewed" ? "Resubmit" : "Submit project"}
                  </button>
                </div>
              )}
            </div>

            {project.status === "submitted" && (
              <div className="ws-project-block">
                <button className="btn-primary" onClick={review} disabled={busy}>
                  {busy ? <Loader2 className="spin" size={15} /> : <Sparkles size={15} />}
                  Request AI review
                </button>
              </div>
            )}

            {project.status === "reviewed" && project.ai_review && (
              <div className="ws-project-block ws-review">
                <strong>
                  <CheckCircle2 size={14} /> AI review · {project.ai_score}/100
                </strong>
                <div className="ws-review-body">{project.ai_review}</div>
                {reviewMeta && (reviewMeta.criteria_met?.length > 0 || reviewMeta.criteria_missed?.length > 0) && (
                  <div className="ws-review-criteria">
                    {reviewMeta.criteria_met?.length > 0 && (
                      <div>
                        <strong>Met</strong>
                        <ul>
                          {reviewMeta.criteria_met.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {reviewMeta.criteria_missed?.length > 0 && (
                      <div>
                        <strong>Needs work</strong>
                        <ul>
                          {reviewMeta.criteria_missed.map((c, i) => (
                            <li key={i}>
                              {c.criterion}
                              {c.why ? ` — ${c.why}` : ""}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                <button className="btn-secondary" onClick={review} disabled={busy}>
                  <XCircle size={14} /> Re-review after fixes
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
