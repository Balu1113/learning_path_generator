import { useState } from "react";
import { placementAdaptiveStart, placementAdaptiveAnswer } from "../api/client";
import { X, Loader2, ChevronRight } from "lucide-react";

const DIFFICULTY_LABEL = { easy: "Easy", medium: "Medium", hard: "Hard" };

export default function PlacementTest({ goal, onDone, onClose }) {
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [answered, setAnswered] = useState(0);

  const start = async () => {
    setLoading(true);
    setError("");
    try {
      const d = await placementAdaptiveStart(goal);
      if (d.error) { setError(d.error); return; }
      setSessionId(d.session_id);
      setQuestion(d.question);
      setSelected(null);
      setAnswered(0);
    } catch {
      setError("Failed to start the test.");
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    if (selected === null) return;
    setLoading(true);
    setError("");
    try {
      const d = await placementAdaptiveAnswer(sessionId, question.id, selected);
      if (d.error) { setError(d.error); return; }
      setAnswered((n) => n + 1);
      if (d.done) {
        setQuestion(null);
        setResult(d.summary);
      } else {
        setQuestion(d.question);
        setSelected(null);
      }
    } catch {
      setError("Failed to submit answer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Placement Test</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        {error && <div className="error-box">{error}</div>}

        {!sessionId && !result && (
          <div className="modal-body">
            <p>
              Answer a short adaptive quiz about <strong>{goal}</strong> and we'll
              suggest your starting level. The test stops as soon as we're confident.
            </p>
            <button className="btn-primary" onClick={start} disabled={loading || !goal.trim()}>
              {loading ? <Loader2 className="spin" size={18} /> : "Start Test"}
            </button>
          </div>
        )}

        {question && !result && (
          <div className="modal-body">
            <div className="placement-progress">
              <span className={`difficulty-badge`} data-level={question.difficulty}>
                {DIFFICULTY_LABEL[question.difficulty] || question.difficulty}
              </span>
              <span className="placement-count">Question {answered + 1}</span>
            </div>
            <div className="quiz-question">
              <p><strong>{question.question}</strong></p>
              <div className="quiz-options">
                {question.options.map((opt, oi) => (
                  <label key={oi} className={`radio-pill ${selected === oi ? "active" : ""}`}>
                    <input
                      type="radio"
                      name="adaptive-q"
                      checked={selected === oi}
                      onChange={() => setSelected(oi)}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={submit}
              disabled={loading || selected === null}
            >
              {loading
                ? <Loader2 className="spin" size={18} />
                : <><ChevronRight size={15} /> Next</>}
            </button>
          </div>
        )}

        {result && (
          <div className="modal-body">
            <div className="placement-result">
              <h3>Score: {result.score}/{result.total} ({result.percent}%)</h3>
              {result.skipped > 0 && (
                <p className="placement-skipped">
                  {result.skipped} question{result.skipped > 1 ? "s" : ""} skipped
                  (test stopped early — confidence reached).
                </p>
              )}
              <p>
                Suggested level:{" "}
                <strong className="level-badge">{result.suggested_level}</strong>
              </p>
              {result.missed?.length > 0 && (
                <details className="placement-missed">
                  <summary>Review {result.missed.length} missed question{result.missed.length > 1 ? "s" : ""}</summary>
                  {result.missed.map((m) => (
                    <div key={m.id} className="placement-missed-item">
                      <p>{m.question}</p>
                      <p className="placement-correct">
                        Correct: option {m.correct_index + 1} · You chose: option {m.user_index + 1}
                      </p>
                    </div>
                  ))}
                </details>
              )}
              <button className="btn-primary" onClick={() => onDone(result.suggested_level)}>
                Use This Level
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
