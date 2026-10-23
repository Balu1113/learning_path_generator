import { useEffect, useState } from "react";
import { getFocusSummary } from "../api/client";
import { Loader2, Pause, Play, Timer, X } from "lucide-react";
import { BREAK_MIN, WORK_OPTIONS, clockLabel, hoursLabel, usePomodoro } from "../pomodoro";

export default function PomodoroPanel({ pathId, phases = [], canLog = false, onClose, initialPhaseIdx = -1, syncPhaseIdx }) {
  const {
    mode, workMin, remaining, running, note,
    toggleRun, reset, setMode, setWorkMin, setCtx, logNow,
  } = usePomodoro();
  const [phaseIdx, setPhaseIdx] = useState(initialPhaseIdx);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (syncPhaseIdx !== undefined) setPhaseIdx(syncPhaseIdx);
  }, [syncPhaseIdx]);

  useEffect(() => {
    setCtx({
      pathId,
      phaseIdx,
      phaseTitle: phaseIdx >= 0 ? (phases[phaseIdx] || "") : "",
      canLog,
    });
  }, [pathId, phaseIdx, phases, canLog, setCtx]);

  useEffect(() => {
    if (!pathId || !canLog) return;
    getFocusSummary(pathId)
      .then((d) => {
        if (!d.error) setSummary(d);
      })
      .catch(() => {});
  }, [pathId, canLog, note]);

  const total = (mode === "work" ? workMin : BREAK_MIN) * 60;
  const pct = total ? Math.round(((total - Math.max(0, remaining)) / total) * 100) : 0;
  const elapsedWork = mode === "work" ? workMin * 60 - Math.max(0, remaining) : 0;
  const canManualLog = canLog && mode === "work" && elapsedWork >= 30;

  return (
    <div className="study-panel pomodoro-panel">
      <div className="study-panel-head">
        <h4><Timer size={16} /> Focus timer</h4>
        {onClose && (
          <button className="modal-close" onClick={onClose} title="Close">
            <X size={16} />
          </button>
        )}
      </div>

      {note && (note.kind === "err"
        ? <div className="error-box">{note.text}</div>
        : <p className="saved-note">{note.text}</p>)}

      <div className="pomodoro-modes">
        <button className={`btn-icon ${mode === "work" ? "active" : ""}`} onClick={() => setMode("work")}>
          Work
        </button>
        <button className={`btn-icon ${mode === "break" ? "active" : ""}`} onClick={() => setMode("break")}>
          Break
        </button>
      </div>

      <div className={`pomodoro-clock ${mode === "break" ? "on-break" : ""}`}>
        <span className="pomodoro-time">{clockLabel(remaining)}</span>
        <span className="pomodoro-label">
          {mode === "work" ? `${workMin} minute focus` : `${BREAK_MIN} minute break`}
          {running ? " · running" : ""}
        </span>
        <div className="pomodoro-bar">
          <div className="pomodoro-bar-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="pomodoro-controls">
        <button className="btn-primary" onClick={toggleRun}>
          {running ? <><Pause size={16} /> Pause</> : <><Play size={16} /> {remaining === total ? "Start" : "Resume"}</>}
        </button>
        <button className="btn-secondary" onClick={reset}>Reset</button>
        {canManualLog && (
          <button className="btn-secondary" onClick={logNow}>
            Log {hoursLabel(elapsedWork)} now
          </button>
        )}
      </div>

      <div className="pomodoro-options">
        {mode === "work" && (
          <div className="pomodoro-durations">
            {WORK_OPTIONS.map((m) => (
              <button
                key={m}
                className={`btn-icon ${workMin === m ? "active" : ""}`}
                onClick={() => setWorkMin(m)}
              >
                {m}m
              </button>
            ))}
          </div>
        )}
        <select value={phaseIdx} onChange={(e) => setPhaseIdx(Number(e.target.value))} title="Phase you are studying">
          <option value={-1}>No specific phase</option>
          {phases.map((t, i) => (
            <option key={i} value={i}>Phase {i + 1}: {t}</option>
          ))}
        </select>
      </div>

      {canLog ? (
        summary ? (
          <div className="deck-stats">
            <span><strong>{hoursLabel(summary.today_seconds || 0)}</strong> today</span>
            <span><strong>{hoursLabel(summary.total_seconds || 0)}</strong> total</span>
            <span><strong>{(summary.by_phase || []).length}</strong> phases practiced</span>
          </div>
        ) : (
          <p className="subtitle"><Loader2 className="spin" size={14} /> Loading focus stats…</p>
        )
      ) : (
        <p className="subtitle">Sign in to track focus time and feed your streak.</p>
      )}
    </div>
  );
}
