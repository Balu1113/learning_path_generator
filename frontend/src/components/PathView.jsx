import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { getProgress, saveProgress, getPhases } from "../api/client";
import { useAuth } from "../auth";
import { CalendarDays, ClipboardCheck, Gauge, Layers, Timer } from "lucide-react";
import { clockLabel, usePomodoro } from "../pomodoro";
import PhaseTest from "./PhaseTest";
import FlashcardsPanel from "./FlashcardsPanel";
import SchedulePanel from "./SchedulePanel";
import PomodoroPanel from "./PomodoroPanel";
import DifficultyPanel from "./DifficultyPanel";

function FocusButton({ open, onClick }) {
  const { running, remaining } = usePomodoro();
  return (
    <button
      className={`btn-icon ${open || running ? "active" : ""}`}
      onClick={onClick}
      title={running ? "Focus timer is running" : "Pomodoro focus timer"}
    >
      <Timer size={14} /> Focus{running ? ` · ${clockLabel(remaining)}` : ""}
    </button>
  );
}


function localKey(pathId) {
  return `progress:${pathId}`;
}

function loadLocal(pathId) {
  try {
    return JSON.parse(localStorage.getItem(localKey(pathId))) || [];
  } catch {
    return [];
  }
}

export default function PathView({ pathId, format, content, hoursPerDay, onVersionCreated, readOnly = false }) {
  const { user } = useAuth();
  const [testPhase, setTestPhase] = useState(null);
  const [panel, setPanel] = useState(null);
  const structured = (() => {
    if (format !== "structured") return null;
    try {
      return typeof content === "string" ? JSON.parse(content) : content;
    } catch {
      return null;
    }
  })();

  const [done, setDone] = useState(() => (pathId ? loadLocal(pathId) : []));
  const [mdPhases, setMdPhases] = useState([]);

  useEffect(() => {
    if (!pathId || structured) return;
    getPhases(pathId)
      .then((d) => setMdPhases(Array.isArray(d.phases) ? d.phases : []))
      .catch(() => setMdPhases([]));
  }, [pathId, structured]);

  useEffect(() => {
    if (!pathId) return;
    setDone(loadLocal(pathId));
    if (user) {
      getProgress(pathId)
        .then((d) => {
          if (Array.isArray(d.done)) setDone(d.done);
        })
        .catch(() => {});
    }
  }, [pathId, user]);

  const totalItems = structured
    ? structured.phases.reduce((acc, ph) => acc + (ph.topics?.length || 0), 0)
    : 0;
  const doneCount = done.filter((k) => k.startsWith("t:")).length;
  const pct = totalItems ? Math.round((doneCount / totalItems) * 100) : 0;

  const phaseTitles = structured
    ? (structured.phases || []).map((ph) => ph.title || "")
    : mdPhases;

  const extras = pathId && !readOnly ? (
    <>
      <div className="path-panels">
        <button
          className={`btn-icon ${panel === "cards" ? "active" : ""}`}
          onClick={() => setPanel((p) => (p === "cards" ? null : "cards"))}
          title="Flashcards with spaced repetition"
        >
          <Layers size={14} /> Flashcards
        </button>
        <button
          className={`btn-icon ${panel === "schedule" ? "active" : ""}`}
          onClick={() => setPanel((p) => (p === "schedule" ? null : "schedule"))}
          title="Daily study schedule with real dates"
        >
          <CalendarDays size={14} /> Schedule
        </button>
        <FocusButton
          open={panel === "pomodoro"}
          onClick={() => setPanel((p) => (p === "pomodoro" ? null : "pomodoro"))}
        />
        <button
          className={`btn-icon ${panel === "difficulty" ? "active" : ""}`}
          onClick={() => setPanel((p) => (p === "difficulty" ? null : "difficulty"))}
          title="Test-score difficulty analysis and phase retuning"
        >
          <Gauge size={14} /> Difficulty
        </button>
      </div>
      {panel === "cards" && (
        <FlashcardsPanel pathId={pathId} onClose={() => setPanel(null)} />
      )}
      {panel === "schedule" && (
        <SchedulePanel pathId={pathId} hoursPerDay={hoursPerDay} onClose={() => setPanel(null)} />
      )}
      {panel === "pomodoro" && (
        <PomodoroPanel
          pathId={pathId}
          phases={phaseTitles}
          canLog={Boolean(user)}
          onClose={() => setPanel(null)}
        />
      )}
      {panel === "difficulty" && (
        <DifficultyPanel
          pathId={pathId}
          onVersionCreated={onVersionCreated}
          onClose={() => setPanel(null)}
        />
      )}
    </>
  ) : null;

  const toggle = (key) => {
    setDone((prev) => {
      const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
      if (pathId) {
        localStorage.setItem(localKey(pathId), JSON.stringify(next));
        if (user) {
          saveProgress(pathId, key, !prev.includes(key)).catch(() => {});
        }
      }
      return next;
    });
  };

  if (!structured) {
    const md = typeof content === "string" ? content : "";
    const canTest = Boolean(pathId && !readOnly && mdPhases.length > 0);

    return (
      <div className="markdown-body md-with-tests">
        {extras}
        <ReactMarkdown>{md}</ReactMarkdown>
        {canTest && (
          <div className="md-phase-tests">
            <p className="md-tests-label">Test yourself by phase</p>
            {mdPhases.map((title, idx) => (
              <button
                key={idx}
                className="btn-icon phase-test-btn"
                onClick={() => setTestPhase(idx)}
              >
                <ClipboardCheck size={14} /> Phase {idx + 1}: {title}
              </button>
            ))}
          </div>
        )}
        {testPhase !== null && pathId && (
          <PhaseTest
            pathId={pathId}
            phaseIdx={testPhase}
            phaseTitle={mdPhases[testPhase] || ""}
            onClose={() => setTestPhase(null)}
          />
        )}
      </div>
    );
  }
  return (
    <div className="path-view">
      {extras}
      <div className="path-view-header">
        <h3>{structured.title}</h3>
        {structured.summary && <p className="path-summary">{structured.summary}</p>}
        <div className="progress-bar-wrap">
          <div className="progress-bar" style={{ width: `${pct}%` }} />
          <span className="progress-label">{doneCount}/{totalItems} topics · {pct}%</span>
        </div>
      </div>
      {structured.phases?.map((phase, pi) => (
        <div key={pi} className="phase-block">
          <h4>
            Phase {pi + 1}: {phase.title}
            {phase.estimated_weeks && <span className="phase-weeks"> · {phase.estimated_weeks} weeks</span>}
            {pathId && !readOnly && (
              <button
                className="btn-icon phase-test-btn"
                title="Test yourself on this phase"
                onClick={() => setTestPhase(pi)}
              >
                <ClipboardCheck size={14} /> Test
              </button>
            )}
          </h4>
          {phase.description && <p className="phase-desc">{phase.description}</p>}
          <div className="topics-list">
            {phase.topics?.map((topic, ti) => {
              const key = `t:${pi}:${ti}`;
              return (
                <div key={key} className={`topic-item ${done.includes(key) ? "done" : ""}`}>
                  {readOnly ? (
                    <div className="topic-check">
                      <strong>{topic.title}</strong>
                    </div>
                  ) : (
                    <label className="topic-check">
                      <input type="checkbox" checked={done.includes(key)} onChange={() => toggle(key)} />
                      <strong>{topic.title}</strong>
                    </label>
                  )}
                  {topic.details && <p className="topic-resources">{topic.details}</p>}
                  {topic.resources?.length > 0 && (
                    <ul className="resource-list">
                      {topic.resources.map((r, ri) => (
                        <li key={ri}>
                          <span className="resource-type">{r.type || "resource"}</span>
                          <strong>{r.name}</strong>
                          {r.note && <span className="resource-note"> — {r.note}</span>}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {testPhase !== null && pathId && (
        <PhaseTest
          pathId={pathId}
          phaseIdx={testPhase}
          phaseTitle={structured.phases?.[testPhase]?.title || ""}
          onClose={() => setTestPhase(null)}
        />
      )}
    </div>
  );
}
