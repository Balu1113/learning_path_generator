import { useCallback, useEffect, useMemo, useState } from "react";
import { generateFlashcards, getFlashcards, reviewFlashcard } from "../api/client";
import { Layers, Loader2, RefreshCw, X } from "lucide-react";
import ReviewSession from "./ReviewSession";

export default function FlashcardsPanel({ pathId, onClose }) {
  const [cards, setCards] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState("completed");
  const [note, setNote] = useState("");
  const [reviewing, setReviewing] = useState(false);

  const load = useCallback(() => {
    getFlashcards(pathId)
      .then((d) => {
        if (d.error) setError(d.error);
        else setCards(d.cards || []);
      })
      .catch(() => setError("Failed to load flashcards."));
  }, [pathId]);

  useEffect(() => {
    setCards(null);
    setError("");
    setReviewing(false);
    setNote("");
    load();
  }, [load]);

  const dueCards = useMemo(() => (cards || []).filter((c) => c.due), [cards]);

  const handleRate = async (card, rating) => {
    const d = await reviewFlashcard(card.id, rating);
    if (d.error) throw new Error(d.error);
    setCards((prev) => (prev || []).map((c) => (c.id === card.id ? d.card : c)));
    return d.card;
  };

  const generate = async () => {
    setBusy(true);
    setError("");
    setNote("");
    try {
      const d = await generateFlashcards(pathId, { source, count: 12 });
      if (d.error) setError(d.error);
      else setNote(`Created ${d.created} card${d.created === 1 ? "" : "s"} from ${d.phases.join(", ") || "your path"}`);
      load();
    } catch {
      setError("Card generation needs the backend LLM to be reachable.");
    }
    setBusy(false);
  };

  return (
    <div className="study-panel flashcards-panel">
      <div className="study-panel-head">
        <h4><Layers size={16} /> Flashcards &amp; spaced repetition</h4>
        {onClose && (
          <button className="modal-close" onClick={onClose} title="Close">
            <X size={16} />
          </button>
        )}
      </div>

      {error && <div className="error-box">{error}</div>}

      {cards === null ? (
        <div className="empty-state small">
          <Loader2 className="spin" size={24} />
          <p>Loading deck...</p>
        </div>
      ) : reviewing ? (
        <ReviewSession
          cards={dueCards}
          onRate={handleRate}
          onExit={() => setReviewing(false)}
        />
      ) : (
        <>
          <div className="deck-stats">
            <span><strong>{cards.length}</strong> cards</span>
            <span><strong>{dueCards.length}</strong> due today</span>
            <span><strong>{cards.filter((c) => c.reps >= 3).length}</strong> learned</span>
          </div>

          <div className="deck-actions">
            <button className="btn-primary" onClick={() => setReviewing(true)} disabled={!dueCards.length}>
              Review {dueCards.length} due card{dueCards.length === 1 ? "" : "s"}
            </button>
            <div className="deck-generate">
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="completed">From completed topics</option>
                <option value="all">From every phase</option>
              </select>
              <button className="btn-secondary" onClick={generate} disabled={busy}>
                {busy ? <Loader2 className="spin" size={14} /> : <RefreshCw size={14} />} Generate cards
              </button>
            </div>
            {note && <p className="saved-note">{note}</p>}
            {cards.length > 0 && !dueCards.length && (
              <p className="subtitle">Nothing is due right now — SM-2 will bring cards back on schedule.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
