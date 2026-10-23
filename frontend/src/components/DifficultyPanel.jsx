import { useCallback, useEffect, useState } from "react";
import { getPathDifficulty, retunePhase } from "../api/client";
import { Gauge, Loader2, TrendingDown, TrendingUp, X } from "lucide-react";

const VERDICTS = {
  too_hard: { label: "Too hard", className: "verdict-hard", Icon: TrendingDown },
  too_easy: { label: "Too easy", className: "verdict-easy", Icon: TrendingUp },
  no_data: { label: "No data", className: "verdict-none", Icon: Gauge },
};

export default function DifficultyPanel({ pathId, onVersionCreated, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(null);

  const load = useCallback(() => {
    setError("");
    getPathDifficulty(pathId)
      .then((d) => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => setError("Failed to load difficulty analysis."));
  }, [pathId]);

  useEffect(() => {
    setData(null);
    load();
  }, [load]);

  const retune = async (phaseIdx, direction) => {
    if (busy !== null) return;
    setBusy(phaseIdx);
    setError("");
    try {
      const d = await retunePhase(pathId, { phase_idx: phaseIdx, direction });
      if (d.error) setError(d.error);
      else {
        setNote(
          `Phase ${phaseIdx + 1} rewritten as ${d.direction} and saved as v${d.version} ` +
          `(progress copied: ${d.copied_progress ? "yes" : "no"}).`,
        );
        if (onVersionCreated) onVersionCreated(d.id);
        load();
      }
    } catch {
      setError("Retuning failed — the model could not be reached.");
    }
    setBusy(null);
  };

  const structured = data?.format === "structured";

  return (
    <div className="study-panel difficulty-panel">
      <div className="study-panel-head">
        <h4><Gauge size={16} /> Difficulty analysis</h4>
        {onClose && (
          <button className="modal-close" onClick={onClose} title="Close">
            <X size={16} />
          </button>
        )}
      </div>

      {error && <div className="error-box">{error}</div>}

      {data === null ? (
        <div className="empty-state small">
          <Loader2 className="spin" size={24} />
          <p>Analyzing your test scores…</p>
        </div>
      ) : (
        <>
          <p className="subtitle">
            Based on your phase test scores{data.phases.every((p) => !p.attempts)
              ? " — take a phase test to unlock verdicts."
              : "."}
          </p>
          <div className="difficulty-list">
            {data.phases.map((p) => {
              const v = VERDICTS[p.verdict] || VERDICTS.no_data;
              const { Icon } = v;
              return (
                <div key={p.phase_idx} className="difficulty-row">
                  <div className="difficulty-info">
                    <strong>Phase {p.phase_idx + 1}: {p.title}</strong>
                    <span className="subtitle">
                      {p.attempts
                        ? `${p.attempts} attempt${p.attempts === 1 ? "" : "s"} · avg ${p.avg_percent}% · last ${p.last_percent}%`
                        : "No tests yet"}
                    </span>
                  </div>
                  <span className={`difficulty-verdict ${v.className}`}>
                    <Icon size={14} /> {v.label}
                  </span>
                  {structured && (
                    <div className="difficulty-actions">
                      <button
                        className="btn-secondary"
                        onClick={() => retune(p.phase_idx, "easier")}
                        disabled={busy !== null}
                        title="Rewrite this phase to be gentler and save a new version"
                      >
                        {busy === p.phase_idx ? <Loader2 className="spin" size={14} /> : <TrendingDown size={14} />} Easier
                      </button>
                      <button
                        className="btn-secondary"
                        onClick={() => retune(p.phase_idx, "harder")}
                        disabled={busy !== null}
                        title="Rewrite this phase to go deeper and save a new version"
                      >
                        <TrendingUp size={14} /> Harder
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          {!structured && (
            <p className="subtitle">Markdown roadmaps can be analyzed but not retuned — regenerate instead.</p>
          )}
          {note && <p className="saved-note">{note}</p>}
        </>
      )}
    </div>
  );
}
