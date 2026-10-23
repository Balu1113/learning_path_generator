import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Eye, Loader2, Repeat, X } from "lucide-react";
import "./ReviewSession.css";

const RATINGS = [
  { value: 0, label: "Again", className: "again" },
  { value: 1, label: "Hard", className: "hard" },
  { value: 2, label: "Good", className: "good" },
  { value: 3, label: "Easy", className: "easy" },
];

function intervalLabel(card) {
  if (!card) return "";
  if (card.reps === 0 || card.interval_days < 1) return "< 1 day";
  if (card.interval_days < 1.5) return "1 day";
  return `${Math.round(card.interval_days)} days`;
}

/** Mirror of the backend SM-2 interval math, used to preview the next gap. */
function previewInterval(card, rating) {
  if (rating === 0) return "10 min";
  const reps = (card?.reps || 0) + 1;
  const ease = Number(card?.ease) || 2.5;
  const interval = Number(card?.interval_days) || 0;
  if (reps === 1) return "1 day";
  if (reps === 2) return "6 days";
  const next = Math.max(1, Math.round(interval * ease));
  if (next >= 60) return `${Math.round(next / 30)} mo`;
  return `${next} days`;
}

export default function ReviewSession({ cards, onRate, onExit, labelFor }) {
  const [total] = useState(() => cards.length);
  const [queue, setQueue] = useState(() => cards.map((c) => c.id));
  const [revealed, setRevealed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [lastCard, setLastCard] = useState(null);

  const current = useMemo(
    () => cards.find((c) => c.id === queue[0]) || null,
    [cards, queue],
  );

  const rate = useCallback(async (rating) => {
    if (!current || busy) return;
    setBusy(true);
    setError("");
    try {
      const updated = await onRate(current, rating);
      setLastCard(updated);
      setQueue((prev) => prev.slice(1));
      setRevealed(false);
      setNote(
        rating === 0
          ? "Scheduled again in ~10 minutes"
          : `Next review in ${intervalLabel(updated)}`,
      );
    } catch (e) {
      setError(e?.message || "Failed to save the review.");
    }
    setBusy(false);
  }, [current, busy, onRate]);

  useEffect(() => {
    if (!current) return undefined;
    const onKey = (e) => {
      const tag = e.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (!revealed) {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          setRevealed(true);
        }
        return;
      }
      const idx = ["1", "2", "3", "4"].indexOf(e.key);
      if (idx >= 0) {
        e.preventDefault();
        rate(idx);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, revealed, rate]);

  if (!current) {
    return (
      <div className="rs-done">
        <span className="rs-done-icon"><CheckCircle2 size={30} /></span>
        <strong>Deck cleared</strong>
        <p>
          You reviewed {total} card{total === 1 ? "" : "s"}.
          {lastCard && note ? ` ${note}.` : ""}
        </p>
        <button className="btn-primary" onClick={onExit}>Back to study hub</button>
      </div>
    );
  }

  const label = labelFor ? labelFor(current) : current.topic;
  const reviewed = total - queue.length;

  return (
    <div className="rs-card">
      <div className="rs-progress">
        <div className="rs-progress-track">
          <div className="rs-progress-fill" style={{ width: `${total ? (reviewed / total) * 100 : 0}%` }} />
        </div>
        <span className="rs-progress-text">{reviewed} / {total} reviewed</span>
      </div>

      <div className="rs-chips">
        {label && <span className="rs-chip accent">{label}</span>}
        {current.phase_idx !== null && current.phase_idx !== undefined && (
          <span className="rs-chip">Phase {current.phase_idx + 1}</span>
        )}
        <span className="rs-chip"><Repeat size={12} /> {current.reps || 0} reps</span>
        <span className="rs-chip">Current gap {intervalLabel(current)}</span>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="rs-flip">
        <div className={`rs-flip-inner ${revealed ? "flipped" : ""}`}>
          <button
            className="rs-face rs-face-front"
            onClick={() => setRevealed(true)}
            tabIndex={revealed ? -1 : 0}
            aria-hidden={revealed}
          >
            <p className="rs-front-text">{current.front}</p>
            <span className="rs-hint">
              <Eye size={14} /> Show the answer
              <kbd>Space</kbd>
            </span>
          </button>
          <div className="rs-face rs-face-back" aria-hidden={!revealed}>
            <p className="rs-back-text">{current.back}</p>
          </div>
        </div>
      </div>

      {revealed ? (
        <div className="rs-ratings">
          {RATINGS.map((r) => (
            <button
              key={r.value}
              className={`rs-rating ${r.className}`}
              disabled={busy}
              onClick={() => rate(r.value)}
            >
              {busy ? <Loader2 className="spin" size={14} /> : null}
              <strong>{r.label}</strong>
              <span>{previewInterval(current, r.value)}</span>
              <kbd>{r.value + 1}</kbd>
            </button>
          ))}
        </div>
      ) : (
        <p className="rs-hint">
          {queue.length} card{queue.length === 1 ? "" : "s"} left · reveal the answer to grade this one.
        </p>
      )}

      <button className="btn-icon exit-review" onClick={onExit}>
        <X size={14} /> Stop reviewing
      </button>
    </div>
  );
}
