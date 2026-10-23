import { useEffect, useMemo, useRef, useState } from "react";
import { getSchedule, scheduleUrl } from "../api/client";
import {
  CalendarDays,
  CalendarRange,
  Download,
  List,
  Loader2,
  Target,
  X,
} from "lucide-react";
import "./SchedulePanel.css";

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function parseISO(iso) {
  return new Date(`${iso}T00:00:00`);
}

function shortDate(iso) {
  return parseISO(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function useDebounced(value, delayMs) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

function WeekRow({ week, todayRef }) {
  return (
    <div className="sch-week">
      <div className="sch-week-head">
        <strong>Week {week.index}</strong>
        <span>{shortDate(week.start)} – {shortDate(week.end)}</span>
        <span className="sch-week-meta">
          {week.blocks} block{week.blocks === 1 ? "" : "s"} · {week.hours}h
        </span>
      </div>
      <div className="sch-week-grid">
        {week.days.map((day) => {
          const isToday = day.date === todayISO();
          return (
            <div
              key={day.date}
              ref={isToday ? todayRef : null}
              className={[
                "sch-cell",
                day.blocks.length ? "has-block" : "off",
                isToday ? "today" : "",
              ].join(" ")}
            >
              <div className="sch-cell-head">
                <span className="sch-cell-num">{parseISO(day.date).getDate()}</span>
              </div>
              {day.blocks.map((b) => (
                <div key={b.id} className="sch-block" title={b.details || b.title}>
                  <span className="sch-block-phase">{b.phase_title}</span>
                  <strong>{b.title}</strong>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function SchedulePanel({ pathId, hoursPerDay, onClose }) {
  const [start, setStart] = useState(todayISO());
  const [daysPerWeek, setDaysPerWeek] = useState(5);
  const [hours, setHours] = useState(() => Number(hoursPerDay) || 2);
  const [view, setView] = useState("calendar");
  const [phase, setPhase] = useState("all");
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const todayRef = useRef(null);

  useEffect(() => {
    if (hoursPerDay) setHours(Number(hoursPerDay) || 2);
  }, [hoursPerDay]);

  const queryKey = useDebounced(
    JSON.stringify({ start, days_per_week: daysPerWeek, hours_per_day: hours }),
    300,
  );
  const query = useMemo(() => JSON.parse(queryKey), [queryKey]);

  useEffect(() => {
    if (!pathId) return undefined;
    let alive = true;
    setLoading(true);
    setError("");
    getSchedule(pathId, query)
      .then((d) => {
        if (!alive) return;
        if (d.error) setError(d.error);
        else setSchedule(d);
      })
      .catch(() => alive && setError("Failed to build the schedule."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [pathId, query]);

  const weeks = useMemo(() => schedule?.weeks || [], [schedule]);
  const phasePlan = schedule?.phase_plan || [];

  const visibleWeeks = useMemo(() => {
    if (phase === "all") return weeks;
    return weeks
      .map((w) => ({
        ...w,
        days: w.days.map((d) => ({
          ...d,
          blocks: d.blocks.filter((b) => b.phase_title === phase),
        })),
      }))
      .filter((w) => w.days.some((d) => d.blocks.length));
  }, [weeks, phase]);

  // Weeks without any block are collapsed into a single "rest / catch-up" row
  // so the calendar stays readable for long roadmaps.
  const calendarRows = useMemo(() => {
    const rows = [];
    let gap = null;
    visibleWeeks.forEach((w) => {
      if (w.blocks === 0) {
        if (gap) gap.to = w.index;
        else gap = { type: "gap", from: w.index, to: w.index };
      } else {
        if (gap) {
          rows.push(gap);
          gap = null;
        }
        rows.push({ type: "week", week: w });
      }
    });
    if (gap) rows.push(gap);
    return rows;
  }, [visibleWeeks]);

  const jumpToToday = () => {
    todayRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const stats = [
    { label: "Study blocks", value: schedule?.total_blocks ?? 0 },
    { label: "Total hours", value: `${schedule?.total_hours ?? 0}h` },
    { label: "Weeks", value: weeks.length },
    { label: "Finishes", value: schedule?.end_date ? shortDate(schedule.end_date) : "—" },
  ];

  return (
    <div className="sch">
      <div className="sch-head">
        <div className="sch-head-title">
          <CalendarDays size={18} />
          <div>
            <h4>Study schedule</h4>
            <p>
              {schedule
                ? `${schedule.total_blocks} blocks across ${weeks.length} weeks · ${schedule.days_per_week} days per week`
                : "Building your plan..."}
            </p>
          </div>
        </div>
        <div className="sch-head-actions">
          <div className="sch-view-toggle" role="group" aria-label="Schedule view">
            <button
              type="button"
              className={view === "calendar" ? "active" : ""}
              onClick={() => setView("calendar")}
              aria-pressed={view === "calendar"}
            >
              <CalendarRange size={14} /> Calendar
            </button>
            <button
              type="button"
              className={view === "list" ? "active" : ""}
              onClick={() => setView("list")}
              aria-pressed={view === "list"}
            >
              <List size={14} /> List
            </button>
          </div>
          <a className="btn-icon" href={scheduleUrl(pathId, query)} download title="Export .ics">
            <Download size={14} /> .ics
          </a>
          <button type="button" className="btn-icon" onClick={jumpToToday} title="Jump to the current week">
            <CalendarDays size={14} /> Today
          </button>
          {onClose && (
            <button className="modal-close" onClick={onClose} title="Close">
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <div className="sch-controls">
        <div className="sch-field">
          <label htmlFor="sch-start">Starts on</label>
          <input
            id="sch-start"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value || todayISO())}
          />
        </div>

        <div className="sch-field">
          <label>Days per week</label>
          <div className="sch-pills" role="group" aria-label="Days per week">
            {[1, 2, 3, 4, 5, 6, 7].map((n) => (
              <button
                key={n}
                type="button"
                className={daysPerWeek === n ? "active" : ""}
                onClick={() => setDaysPerWeek(n)}
                aria-pressed={daysPerWeek === n}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <div className="sch-field">
          <label htmlFor="sch-hours">Hours per day</label>
          <div className="sch-stepper">
            <button
              type="button"
              onClick={() => setHours((h) => Math.max(0.5, Number((h - 0.5).toFixed(1))))}
              aria-label="Fewer hours per day"
            >
              −
            </button>
            <input
              id="sch-hours"
              type="number"
              min="0.5"
              max="12"
              step="0.5"
              value={hours}
              onChange={(e) => setHours(Math.min(12, Math.max(0.5, Number(e.target.value) || 0.5)))}
            />
            <button
              type="button"
              onClick={() => setHours((h) => Math.min(12, Number((h + 0.5).toFixed(1))))}
              aria-label="More hours per day"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loading ? (
        <div className="empty-state small">
          <Loader2 className="spin" size={24} />
          <p>Building blocks with real dates...</p>
        </div>
      ) : schedule ? (
        <>
          <div className="sch-stats">
            {stats.map((s) => (
              <div className="sch-stat" key={s.label}>
                <strong>{s.value}</strong>
                <span>{s.label}</span>
              </div>
            ))}
          </div>

          {phasePlan.length > 0 && (
            <div className="sch-phase-plan">
              {phasePlan.map((p, i) => (
                <div className="sch-phase" key={p.title}>
                  <span className="sch-phase-index">{i + 1}</span>
                  <div className="sch-phase-body">
                    <strong>{p.title}</strong>
                    <span>
                      {p.blocks} block{p.blocks === 1 ? "" : "s"} · {p.hours}h · {shortDate(p.start)} – {shortDate(p.end)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {(schedule.phases || []).length > 1 && (
            <div className="sch-filters">
              <button
                type="button"
                className={phase === "all" ? "active" : ""}
                onClick={() => setPhase("all")}
              >
                All phases
              </button>
              {schedule.phases.map((title) => (
                <button
                  key={title}
                  type="button"
                  className={phase === title ? "active" : ""}
                  onClick={() => setPhase(title)}
                >
                  {title}
                </button>
              ))}
            </div>
          )}

          {visibleWeeks.length === 0 ? (
            <div className="empty-state small">
              <Target size={24} />
              <p>No blocks match this filter.</p>
            </div>
          ) : view === "calendar" ? (
            <div className="sch-calendar">
              <div className="sch-weekdays">
                {WEEKDAY_LABELS.map((label) => (
                  <span key={label}>{label}</span>
                ))}
              </div>

              {calendarRows.map((row) =>
                row.type === "gap" ? (
                  <div className="sch-gap" key={`gap-${row.from}`}>
                    <CalendarRange size={14} />
                    <span>
                      Week{row.from !== row.to ? "s" : ""} {row.from}
                      {row.from !== row.to ? `–${row.to}` : ""} · catch-up, review and rest
                    </span>
                  </div>
                ) : (
                  <WeekRow key={row.week.index} week={row.week} todayRef={todayRef} />
                ),
              )}
            </div>
          ) : (
            <div className="sch-list">
              {visibleWeeks.filter((w) => w.days.some((d) => d.blocks.length)).map((week) => (
                <div className="sch-list-week" key={week.index}>
                  <div className="sch-list-week-head">
                    <strong>Week {week.index}</strong>
                    <span>{shortDate(week.start)} – {shortDate(week.end)}</span>
                    <span className="sch-week-meta">
                      {week.blocks} block{week.blocks === 1 ? "" : "s"} · {week.hours}h
                    </span>
                  </div>
                  {week.days.filter((d) => d.blocks.length).map((day) => (
                    <div key={day.date} className="sch-list-day">
                      <div className="sch-list-date">
                        <strong>{parseISO(day.date).toLocaleDateString(undefined, { weekday: "short" })}</strong>
                        <span>{shortDate(day.date)}</span>
                      </div>
                      <div className="sch-list-blocks">
                        {day.blocks.map((b) => (
                          <div key={b.id} className="sch-list-block">
                            <span className="sch-block-phase">{b.phase_title}</span>
                            <strong>{b.title}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {schedule.days_per_week < 7 && (
            <p className="sch-note">
              You are studying {schedule.days_per_week} days a week. The remaining days are kept free for review,
              catch-up and rest.
            </p>
          )}
        </>
      ) : null}
    </div>
  );
}
