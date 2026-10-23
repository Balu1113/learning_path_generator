import { useEffect, useMemo, useState } from "react";
import { getStreak } from "../api/client";
import { Flame, Loader2, Target } from "lucide-react";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Mon", "", "Wed", "", "Fri", "", "Sun"];

function level(count) {
  if (!count) return 0;
  if (count === 1) return 1;
  if (count <= 3) return 2;
  if (count <= 6) return 3;
  return 4;
}

function iso(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function StreakHeatmap({ days = 182, data: provided }) {
  const controlled = provided !== undefined;
  const [data, setData] = useState(controlled ? provided : null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(!controlled);

  useEffect(() => {
    if (controlled) {
      setData(provided);
      setError("");
      setLoading(false);
      return undefined;
    }
    let alive = true;
    setLoading(true);
    getStreak(days)
      .then((d) => {
        if (!alive) return;
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => alive && setError("Sign in to track your study streak."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [days, controlled, provided]);

  const grid = useMemo(() => {
    if (!data?.series?.length) return null;
    const byDate = Object.fromEntries(data.series.map((d) => [d.date, d.count]));
    const first = new Date(`${data.series[0].date}T00:00:00`);
    const last = new Date(`${data.series[data.series.length - 1].date}T00:00:00`);

    const start = new Date(first);
    start.setDate(start.getDate() - start.getDay());

    const weeks = [];
    let week = [];
    const cursor = new Date(start);
    while (cursor <= last) {
      week.push({ date: iso(cursor), count: byDate[iso(cursor)] || 0, inRange: cursor >= first });
      if (week.length === 7) {
        weeks.push(week);
        week = [];
      }
      cursor.setDate(cursor.getDate() + 1);
    }
    if (week.length) {
      while (week.length < 7) week.push({ date: "", count: 0, inRange: false });
      weeks.push(week);
    }

    const monthLabels = weeks.map((w) => {
      const d = new Date(`${w[0].date}T00:00:00`);
      return w[0].date && d.getDate() <= 7 ? MONTHS[d.getMonth()] : "";
    });

    return { weeks, monthLabels, today: iso(new Date()) };
  }, [data]);

  if (error) return <div className="error-box">{error}</div>;
  if (!data || !grid || loading) {
    return (
      <div className="empty-state small">
        <Loader2 className="spin" size={24} />
        <p>Loading streak...</p>
      </div>
    );
  }

  return (
    <div className="streak-block">
      <div className="study-heat-stats">
        <div className="study-heat-stat">
          <strong><Flame size={17} /> {data.current_streak}</strong>
          <span>Current streak</span>
        </div>
        <div className="study-heat-stat">
          <strong><Target size={17} /> {data.longest_streak}</strong>
          <span>Longest streak</span>
        </div>
        <div className="study-heat-stat">
          <strong>{data.active_days}</strong>
          <span>Active days</span>
        </div>
        <div className="study-heat-stat">
          <strong>{data.total_sessions}</strong>
          <span>Sessions logged</span>
        </div>
      </div>

      <div className="heatmap-scroll">
        <div className="heatmap">
          <div className="heatmap-months">
            {grid.monthLabels.map((m, i) => (
              <span key={i}>{m}</span>
            ))}
          </div>
          <div className="heatmap-grid">
            <div className="study-heat-weekdays">
              {WEEKDAYS.map((d, i) => (
                <span key={i}>{d}</span>
              ))}
            </div>
            {grid.weeks.map((week, wi) => (
              <div key={wi} className="heatmap-col">
                {week.map((cell, ci) => (
                  <div
                    key={cell.date || `pad-${wi}-${ci}`}
                    className={[
                      "heat-cell",
                      !cell.date ? "empty" : cell.inRange ? `l${level(cell.count)}` : "out",
                      cell.date === grid.today ? "today" : "",
                    ].join(" ")}
                    title={cell.date && cell.inRange ? `${cell.count} session${cell.count === 1 ? "" : "s"} on ${cell.date}` : ""}
                  />
                ))}
              </div>
            ))}
          </div>
          <div className="heatmap-legend">
            <span>Less</span>
            <i className="heat-cell l0" />
            <i className="heat-cell l1" />
            <i className="heat-cell l2" />
            <i className="heat-cell l3" />
            <i className="heat-cell l4" />
            <span>More</span>
          </div>
        </div>
      </div>
    </div>
  );
}
