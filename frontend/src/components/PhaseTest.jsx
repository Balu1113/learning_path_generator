import { useState } from "react";
import { phaseTestStart, phaseTestSubmit } from "../api/client";
import { X, Loader2, Plus, CheckCircle2, XCircle } from "lucide-react";

export default function PhaseTest({ pathId, phaseIdx, phaseTitle, onClose }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [asked, setAsked] = useState([]);
  const [sessionScore, setSessionScore] = useState({ correct: 0, total: 0 });
  const [rounds, setRounds] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const start = async (avoid = []) => {
    setLoading(true);
    setError("");
    try {
      const d = await phaseTestStart(pathId, phaseIdx, { count: 5, avoid });
      if (d.error) setError(d.error);
      else {
        setQuiz(d);
        setAnswers({});
        setResult(null);
        setAsked((prev) => [...prev, ...(d.questions || []).map((q) => q.question)]);
      }
    } catch {
      setError("Failed to generate the test.");
    }
    setLoading(false);
  };

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      const d = await phaseTestSubmit(quiz.quiz_id, answers);
      if (d.error) setError(d.error);
      else {
        setResult(d);
        setSessionScore((s) => ({ correct: s.correct + d.score, total: s.total + d.total }));
        setRounds((r) => r + 1);
      }
    } catch {
      setError("Failed to submit answers.");
    }
    setLoading(false);
  };

  const answered = quiz ? quiz.questions.every((q) => answers[q.id] !== undefined) : false;

  const startRemediation = () => {
    if (!result?.remediation) return;
    setQuiz({
      quiz_id: result.remediation.quiz_id,
      questions: result.remediation.questions,
    });
    setAnswers({});
    setResult(null);
    setAsked((prev) => [...prev, ...result.remediation.questions.map((q) => q.question)]);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Phase Test{phaseTitle ? ` — ${phaseTitle}` : ""}</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        {error && <div className="error-box">{error}</div>}

        {!quiz && !result && (
          <div className="modal-body">
            <p>Test your understanding of <strong>{phaseTitle}</strong> with 5 multiple-choice questions. After finishing you can request more questions as many times as you like.</p>
            {rounds > 0 && (
              <p className="subtitle">
                Session score: {sessionScore.correct}/{sessionScore.total} across {rounds} round{rounds === 1 ? "" : "s"}
              </p>
            )}
            <button className="btn-primary" onClick={() => start(asked)} disabled={loading}>
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
              <h3>This round: {result.score}/{result.total} ({result.percent}%)</h3>
              <p className="subtitle">
                Session: {sessionScore.correct}/{sessionScore.total} across {rounds} round{rounds === 1 ? "" : "s"}
              </p>
              <div className="test-review">
                {result.results.map((r, i) => (
                  <div key={r.id} className={`test-review-item ${r.correct ? "ok" : "bad"}`}>
                    {r.correct ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
                    <span>Q{i + 1}{r.correct ? "" : ` — correct answer: option ${r.correct_index + 1}`}</span>
                  </div>
                ))}
              </div>
              <div className="modal-actions">
                {result.remediation && (
                  <button className="btn-primary" onClick={startRemediation}>
                    <Plus size={16} /> Practice {result.remediation.count} missed question{result.remediation.count === 1 ? "" : "s"}
                  </button>
                )}
                <button className="btn-primary" onClick={() => start(asked)} disabled={loading}>
                  {loading ? <Loader2 className="spin" size={18} /> : <><Plus size={16} /> More questions</>}
                </button>
                <button className="btn-secondary" onClick={onClose}>Done</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
