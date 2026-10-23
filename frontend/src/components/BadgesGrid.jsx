import { useEffect, useState } from "react";
import { getBadges } from "../api/client";
import { Award, ClipboardCheck, Flag, Flame, Layers, Loader2, Lock, Target, Trophy } from "lucide-react";

const ICONS = {
  Flag,
  Layers,
  Trophy,
  Target,
  Flame,
  ClipboardCheck,
};

export default function BadgesGrid({ data: provided, limit }) {
  const controlled = provided !== undefined;
  const [badges, setBadges] = useState(controlled ? provided : null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (controlled) {
      setBadges(provided);
      setError("");
      return undefined;
    }
    let alive = true;
    getBadges()
      .then((d) => {
        if (!alive) return;
        if (d.error) setError(d.error);
        else setBadges(d.badges || []);
      })
      .catch(() => alive && setError("Sign in to see your badges."));
    return () => {
      alive = false;
    };
  }, [controlled, provided]);

  if (error) return <div className="error-box">{error}</div>;
  if (!badges) {
    return (
      <div className="empty-state small">
        <Loader2 className="spin" size={24} />
        <p>Loading badges...</p>
      </div>
    );
  }

  const earned = badges.filter((b) => b.earned).length;
  const pct = badges.length ? Math.round((earned / badges.length) * 100) : 0;
  const visible = limit
    ? [...badges].sort((a, b) => Number(b.earned) - Number(a.earned)).slice(0, limit)
    : badges;

  return (
    <div>
      <div className="study-badge-summary">
        <div className="study-badge-track">
          <div className="study-badge-track-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="study-badge-count">{earned} / {badges.length} unlocked</span>
      </div>

      <div className="study-badge-grid">
        {visible.map((b) => {
          const Icon = ICONS[b.icon] || Award;
          return (
            <div key={b.key} className={`study-badge ${b.earned ? "earned" : "locked"}`}>
              <div className="study-badge-icon">
                {b.earned ? <Icon size={21} /> : <Lock size={18} />}
              </div>
              <strong>{b.name}</strong>
              <p>{b.description}</p>
              {b.earned && b.earned_at && (
                <span className="study-badge-date">
                  Earned {new Date(b.earned_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
