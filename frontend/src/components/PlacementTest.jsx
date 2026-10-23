import { useState } from "react";
import { placementStart, placementSubmit } from "../api/client";
import { X, Loader2 } from "lucide-react";

export default function PlacementTest({ goal, onDone, onClose }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const start = async () => {
    setLoading(true);
    setError("");
    try {
      const d = await placementStart(goal);
      if (d.error) setError(d.error);
      else {
        setQuiz(d);
        setAnswers({});
      }
    } catch {
      setError("Failed to start the test.");
    }
    setLoading(false);
  };

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      const d = await placementSubmit(quiz.quiz_id, answers);
      if (d.error) setError(d.error);
      else setResult(d);
    } catch {
      setError("Failed to submit answers.");
    }
    setLoading(false);
  };

  const answered = quiz ? quiz.questions.every((q) => answers[q.id] !== undefined) : false;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Placement Test</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        {error && <div className="error-box">{error}</div>}

        {!quiz && !result && (
          <div className="modal-body">
            <p>Answer 5 quick multiple-choice questions about <strong>{goal}</strong> and we'll suggest your level.</p>
            <button className="btn-primary" onClick={start} disabled={loading || !goal.trim()}>
              {loading ? <Loader2 className="spin" size={18} /> : "Start Test"}
            </button>
          </div>
        )}

        {quiz && !result && (
          <div className="modal-body">
            {quiz.questions.map((q, qi) => (
              <div key={q.id} className="quiz-question">
                <p><strong>Q{qi + 1}.</strong> {q.question}</p>
                <div className="quiz-options">
                  {q.options.map((opt, oi) => (
                    <label key={oi} className={`radio-pill ${answers[q.id] === oi ? "active" : ""}`}>
                      <input
                        type="radio"
                        name={q.id}
                        checked={answers[q.id] === oi}
                        onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: oi }))}
                      />
                      {opt}
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button className="btn-primary" onClick={submit} disabled={loading || !answered}>
              {loading ? <Loader2 className="spin" size={18} /> : "Submit Answers"}
            </button>
          </div>
        )}

        {result && (
          <div className="modal-body">
            <div className="placement-result">
              <h3>Score: {result.score}/{result.total} ({result.percent}%)</h3>
              <p>
                Suggested level: <strong className="level-badge">{result.suggested_level}</strong>
              </p>
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
