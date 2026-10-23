import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getBadges,
  getDueFlashcards,
  getPathHistory,
  getPathWorkspace,
  getStreak,
  reviewFlashcard,
  saveProgress,
} from "../api/client";
import { useAuth } from "../auth";
import StreakHeatmap from "../components/StreakHeatmap";
import BadgesGrid from "../components/BadgesGrid";
import SchedulePanel from "../components/SchedulePanel";
import ReviewSession from "../components/ReviewSession";
import PomodoroPanel from "../components/PomodoroPanel";
import ChatPanel from "../components/ChatPanel";
import PhaseTest from "../components/PhaseTest";
import StudyNotesModal from "../components/StudyNotesModal";
import {
  Award,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Flame,
  Layers,
  Loader2,
  LogIn,
  PlayCircle,
  Sparkles,
  Target,
  Timer,
  X,
} from "lucide-react";
import "./Study.css";

function localProgressKey(pathId) {
  return `progress:${pathId}`;
}

function loadLocalProgress(pathId) {
  try {
    return JSON.parse(localStorage.getItem(localProgressKey(pathId))) || [];
  } catch {
    return [];
  }
}

function firstIncompletePhase(phases, doneKeys) {
  const i = phases.findIndex((ph) => (ph.topics || []).some((t) => !doneKeys.includes(t.key)));
  return i >= 0 ? i : 0;
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export default function Study() {
  const { user, loading: authLoading } = useAuth();

  const [paths, setPaths] = useState([]);
  const [pathId, setPathId] = useState("");
  const [ws, setWs] = useState(null);
  const [wsLoading, setWsLoading] = useState(false);
  const [done, setDone] = useState([]);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [error, setError] = useState("");

  const [due, setDue] = useState(null);
  const [streak, setStreak] = useState(null);
  const [badges, setBadges] = useState(null);

  const [modal, setModal] = useState(null);
  const [reviewing, setReviewing] = useState(false);
  const [notesTopic, setNotesTopic] = useState(null);

  useEffect(() => {
    getPathHistory()
      .then((d) => {
        const list = d.paths || [];
        setPaths(list);
        if (list.length) {
          const saved = localStorage.getItem("study:path");
          const pick = list.find((p) => p.id === saved) ? saved : list[0].id;
          setPathId(pick);
        }
      })
      .catch(() => setError("Failed to load your paths."));
  }, []);

  useEffect(() => {
    if (!pathId) {
      setWs(null);
      setDone([]);
      return undefined;
    }
    let alive = true;
    setWsLoading(true);
    getPathWorkspace(pathId)
      .then((d) => {
        if (!alive) return;
        if (d.error) {
          setError(d.error);
          setWs(null);
          return;
        }
        setWs(d);
        const server = Array.isArray(d.done) ? d.done : [];
        const merged = Array.from(new Set([...loadLocalProgress(pathId), ...server]));
        setDone(merged);
        const phases = d.phases || [];
        const savedIdx = Number(localStorage.getItem(`study:phase:${pathId}`));
        const valid = Number.isInteger(savedIdx) && savedIdx >= 0 && savedIdx < phases.length;
        setPhaseIdx(valid ? savedIdx : firstIncompletePhase(phases, merged));
      })
      .catch(() => alive && setError("Failed to load the study workspace for this roadmap."))
      .finally(() => alive && setWsLoading(false));
    return () => {
      alive = false;
    };
  }, [pathId]);

  useEffect(() => {
    if (!user) {
      setDue(null);
      setStreak(null);
      setBadges(null);
      return;
    }
    getDueFlashcards(50)
      .then((d) => {
        if (d.error) setError(d.error);
        else setDue(d);
      })
      .catch(() => {});
    getStreak(182)
      .then((d) => {
        if (!d.error) setStreak(d);
      })
      .catch(() => {});
    getBadges()
      .then((d) => {
        if (!d.error) setBadges(d.badges || []);
      })
      .catch(() => {});
  }, [user]);

  const phaseList = useMemo(() => ws?.phases || [], [ws]);
  const current = phaseList[phaseIdx] || null;

  const totalTopics = phaseList.reduce((a, ph) => a + (ph.topics?.length || 0), 0);
  const doneCount = phaseList.reduce(
    (a, ph) => a + (ph.topics || []).filter((t) => done.includes(t.key)).length,
    0,
  );
  const pct = totalTopics ? Math.round((doneCount / totalTopics) * 100) : 0;

  const currentDone = current ? current.topics.filter((t) => done.includes(t.key)).length : 0;
  const currentComplete = Boolean(current && current.topics.length > 0 && currentDone === current.topics.length);

  const dueCards = due?.cards || [];
  const dueCount = due?.count || 0;
  const earnedBadges = (badges || []).filter((b) => b.earned).length;

  const selectPhase = (i) => {
    setPhaseIdx(i);
    if (pathId) localStorage.setItem(`study:phase:${pathId}`, String(i));
  };

  const toggleTopic = (key) => {
    if (!pathId) return;
    setDone((prev) => {
      const was = prev.includes(key);
      const next = was ? prev.filter((k) => k !== key) : [...prev, key];
      localStorage.setItem(localProgressKey(pathId), JSON.stringify(next));
      if (user) saveProgress(pathId, key, !was).catch(() => {});
      return next;
    });
  };

  const handleRate = async (card, rating) => {
    const d = await reviewFlashcard(card.id, rating);
    if (d.error) throw new Error(d.error);
    setDue((prev) => ({
      ...prev,
      count: Math.max(0, (prev?.count || 1) - 1),
      cards: (prev?.cards || []).filter((c) => c.id !== card.id),
    }));
    return d.card;
  };

  if (authLoading) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Opening your study workspace...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="page-container study-page">
        <div className="study-guest">
          <div className="study-guest-card">
            <div className="study-card-title"><BookOpen size={20} /> Study workspace</div>
            <h2>One screen to actually do the work</h2>
            <p>
              Pick a roadmap and land on the next unfinished phase: a topic checklist with
              real resources, a phase-focused timer, a knowledge test, and an AI tutor —
              all in one place. Progress syncs to your roadmap and keeps your streak alive.
            </p>
            <Link to="/login" className="btn-primary study-btn-lg">
              <LogIn size={16} /> Log in to start studying
            </Link>
          </div>

          <div className="study-feature-list">
            <div className="study-feature">
              <Target size={18} />
              <div>
                <strong>Phase-by-phase checklist</strong>
                <span>Check off topics with curated resources as you finish them.</span>
              </div>
            </div>
            <div className="study-feature">
              <Timer size={18} />
              <div>
                <strong>Focus timer</strong>
                <span>Pomodoro sessions bound to the phase you are studying.</span>
              </div>
            </div>
            <div className="study-feature">
              <ClipboardCheck size={18} />
              <div>
                <strong>Phase tests</strong>
                <span>Quiz yourself the moment you finish a phase, with remediation.</span>
              </div>
            </div>
            <div className="study-feature">
              <Flame size={18} />
              <div>
                <strong>Reviews &amp; streaks</strong>
                <span>Due flashcards, focus time and progress all feed one streak.</span>
              </div>
            </div>
          </div>
        </div>

        {paths.length > 0 && (
          <SchedulePanel pathId={paths[0].id} hoursPerDay={paths[0].hours_per_day} />
        )}
      </div>
    );
  }

  const closeReview = () => {
    setModal(null);
    setReviewing(false);
  };

  return (
    <div className="page-container study-page">
      <header className="ws-topbar">
        <div className="ws-pick">
          <span className="ws-eyebrow"><BookOpen size={13} /> Study workspace</span>
          <select
            value={pathId}
            onChange={(e) => {
              setPathId(e.target.value);
              localStorage.setItem("study:path", e.target.value);
            }}
            aria-label="Choose a roadmap to study"
          >
            {paths.map((p) => (
              <option key={p.id} value={p.id}>
                {p.goal}{p.version > 1 ? ` (v${p.version})` : ""}
              </option>
            ))}
          </select>
          {ws?.hours_per_day && <span className="ws-chip quiet">{ws.hours_per_day}h/day</span>}
          {ws?.total_weeks && <span className="ws-chip quiet">~{ws.total_weeks} weeks</span>}
        </div>

        <div className="ws-overall">
          <div className="ws-overall-bar">
            <div className="ws-overall-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="ws-overall-label">{doneCount}/{totalTopics} topics · {pct}%</span>
        </div>

        <div className="ws-chips">
          <button className="ws-chip-btn" onClick={() => setModal("streak")} title="Study streak heatmap">
            <Flame size={14} /> {streak?.current_streak ?? 0}-day
          </button>
          <button
            className={`ws-chip-btn ${dueCount > 0 ? "accent" : ""}`}
            onClick={() => setModal("review")}
            title="Flashcards due for review"
          >
            <Layers size={14} /> {dueCount} due
          </button>
          <button className="ws-chip-btn" onClick={() => setModal("schedule")} title="Weekly study schedule">
            <CalendarDays size={14} /> Plan
          </button>
          <button className="ws-chip-btn" onClick={() => setModal("badges")} title="Achievements">
            <Award size={14} /> {earnedBadges}
          </button>
        </div>
      </header>

      {error && <div className="error-box">{error}</div>}

      {wsLoading ? (
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Loading your workspace...</p>
        </div>
      ) : paths.length === 0 ? (
        <section className="study-card ws-empty-card">
          <div className="study-empty">
            <span className="study-empty-icon"><Sparkles size={26} /></span>
            <strong>No roadmap yet</strong>
            <p>Generate a roadmap and it becomes your study workspace — phases, topics and all.</p>
            <Link to="/quick" className="btn-primary"><Sparkles size={16} /> Create a roadmap</Link>
          </div>
        </section>
      ) : phaseList.length === 0 ? (
        <section className="study-card ws-empty-card">
          <div className="study-empty">
            <span className="study-empty-icon"><BookOpen size={26} /></span>
            <strong>No phases detected in this roadmap</strong>
            <p>
              This roadmap could not be split into phases. Open it in your history to read it,
              or regenerate it as an interactive checklist.
            </p>
            <Link to="/history" className="btn-secondary">Open path history</Link>
          </div>
        </section>
      ) : (
        <div className="ws-grid">
          <aside className="ws-phases" aria-label="Roadmap phases">
            {phaseList.map((ph, i) => {
              const t = ph.topics?.length || 0;
              const d = ph.topics?.filter((x) => done.includes(x.key)).length || 0;
              const complete = t > 0 && d === t;
              return (
                <button
                  key={i}
                  className={`ws-phase-item ${i === phaseIdx ? "active" : ""} ${complete ? "complete" : ""}`}
                  onClick={() => selectPhase(i)}
                >
                  <span className="ws-phase-num">
                    {complete ? <CheckCircle2 size={13} /> : i + 1}
                  </span>
                  <span className="ws-phase-body">
                    <strong>{ph.title}</strong>
                    <small>
                      {d}/{t} topics{ph.estimated_weeks ? ` · ~${ph.estimated_weeks}w` : ""}
                    </small>
                    <span className="ws-phase-bar">
                      <span style={{ width: `${t ? (d / t) * 100 : 0}%` }} />
                    </span>
                  </span>
                </button>
              );
            })}
          </aside>

          <main className="ws-main">
            {current && (
              <section className="study-card ws-focus-card">
                <div className="study-card-head">
                  <div>
                    <div className="study-card-title">
                      <Target size={17} /> Phase {phaseIdx + 1} · {current.title}
                    </div>
                    <div className="study-card-sub">
                      {currentDone}/{current.topics.length} topics done
                      {current.estimated_weeks ? ` · about ${current.estimated_weeks} weeks` : ""}
                    </div>
                  </div>
                  <button className="btn-secondary" onClick={() => setModal({ test: phaseIdx })}>
                    <ClipboardCheck size={15} /> Test this phase
                  </button>
                </div>
                <div className="study-card-body">
                  {current.description && <p className="ws-phase-desc">{current.description}</p>}
                  <div className="ws-topics">
                    {current.topics.map((t) => {
                      const isDone = done.includes(t.key);
                      return (
                        <div key={t.key} className={`ws-topic ${isDone ? "done" : ""}`}>
                          <div className="ws-topic-row">
                            <label className="ws-topic-check">
                              <input
                                type="checkbox"
                                checked={isDone}
                                onChange={() => toggleTopic(t.key)}
                              />
                              <span>
                                <strong>{t.title}</strong>
                                {t.details && <em>{t.details}</em>}
                              </span>
                            </label>
                            <button
                              className="ws-topic-notes"
                              title="In-depth study notes for this topic"
                              onClick={() =>
                                setNotesTopic({ phaseIdx, topicIdx: t.index, title: t.title })
                              }
                            >
                              <BookOpen size={13} /> Notes
                            </button>
                          </div>
                          {t.resources?.length > 0 && (
                            <ul className="ws-resources">
                              {t.resources.map((r, ri) => (
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
                  <div className="ws-phase-footer">
                    {currentComplete ? (
                      <div className="ws-complete-note">
                        <span><CheckCircle2 size={16} /> Phase complete — test yourself or move on.</span>
                        {phaseIdx < phaseList.length - 1 && (
                          <button className="btn-primary" onClick={() => selectPhase(phaseIdx + 1)}>
                            Next: {phaseList[phaseIdx + 1].title} <ChevronRight size={15} />
                          </button>
                        )}
                      </div>
                    ) : (
                      <p className="study-card-sub">
                        Check off each topic as you finish it — progress syncs with your roadmap
                        and feeds your streak.
                      </p>
                    )}
                  </div>
                </div>
              </section>
            )}
          </main>

          <aside className="ws-tools">
            <PomodoroPanel
              pathId={pathId}
              phases={phaseList.map((p) => p.title)}
              canLog={Boolean(user)}
              syncPhaseIdx={phaseIdx}
            />
            <div className="ws-chat-wrap">
              <ChatPanel pathId={pathId} />
            </div>
          </aside>
        </div>
      )}

      {modal === "review" && (
        <div className="modal-overlay" onClick={closeReview}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Flashcard review</h3>
              <button className="modal-close" onClick={closeReview}><X size={18} /></button>
            </div>
            <div className="modal-body">
              {!due ? (
                <div className="empty-state small">
                  <Loader2 className="spin" size={24} />
                  <p>Loading your deck...</p>
                </div>
              ) : reviewing && dueCards.length ? (
                <ReviewSession
                  cards={dueCards}
                  onRate={handleRate}
                  onExit={() => setReviewing(false)}
                  labelFor={(c) => due.paths?.[c.path_id] || c.topic}
                />
              ) : dueCards.length ? (
                <div className="study-cta">
                  <p>
                    {dueCount} card{dueCount === 1 ? "" : "s"} across{" "}
                    {Object.keys(due?.paths || {}).length} roadmap
                    {Object.keys(due?.paths || {}).length === 1 ? "" : "s"} are due.
                    Cards reschedule themselves with SM-2 after each rating.
                  </p>
                  <button className="btn-primary study-btn-lg" onClick={() => setReviewing(true)}>
                    <PlayCircle size={18} /> Start review · {dueCount} card{dueCount === 1 ? "" : "s"}
                  </button>
                </div>
              ) : (
                <div className="study-empty">
                  <span className="study-empty-icon"><CheckCircle2 size={26} /></span>
                  <strong>All caught up</strong>
                  <p>No cards are due right now. New cards appear when their interval arrives.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {modal === "schedule" && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal-box ws-modal-wide" onClick={(e) => e.stopPropagation()}>
            <SchedulePanel
              pathId={pathId}
              hoursPerDay={ws?.hours_per_day}
              onClose={() => setModal(null)}
            />
          </div>
        </div>
      )}

      {modal === "streak" && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal-box ws-modal-wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Study streak</h3>
              <button className="modal-close" onClick={() => setModal(null)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <StreakHeatmap days={182} data={streak} />
            </div>
          </div>
        </div>
      )}

      {modal === "badges" && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal-box ws-modal-wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Achievements · {earnedBadges}/{badges?.length ?? 0} unlocked</h3>
              <button className="modal-close" onClick={() => setModal(null)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <BadgesGrid data={badges} />
            </div>
          </div>
        </div>
      )}

      {modal?.test !== undefined && (
        <PhaseTest
          pathId={pathId}
          phaseIdx={modal.test}
          phaseTitle={phaseList[modal.test]?.title || ""}
          onClose={() => setModal(null)}
        />
      )}

      {notesTopic && (
        <StudyNotesModal
          pathId={pathId}
          phaseIdx={notesTopic.phaseIdx}
          topicIdx={notesTopic.topicIdx}
          topicTitle={notesTopic.title}
          onClose={() => setNotesTopic(null)}
        />
      )}
    </div>
  );
}
