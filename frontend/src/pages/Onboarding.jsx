import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { pathStream, pathStreamSave, pathStructured } from "../api/client";
import ReactMarkdown from "react-markdown";
import PlacementTest from "../components/PlacementTest";
import PathView from "../components/PathView";
import {
  ArrowLeft, ArrowRight, CheckCircle2, ClipboardCheck, Loader2, Rocket, Wand2, X, Zap,
} from "lucide-react";

const LEVELS = ["beginner", "intermediate", "advanced"];
const FORMATS = [
  "courses and hands-on projects",
  "books and documentation",
  "video tutorials",
  "mix of all formats",
];
const STEPS = ["Goal", "Level", "Pace", "Generate"];
const EXAMPLES = [
  "Become a Full Stack Web Developer",
  "Learn Machine Learning",
  "Get into Cybersecurity",
  "Master AWS Cloud Engineering",
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("beginner");
  const [hours, setHours] = useState(2);
  const [months, setMonths] = useState(6);
  const [fmt, setFmt] = useState(FORMATS[0]);
  const [targetDate, setTargetDate] = useState("");
  const [mode, setMode] = useState("structured");
  const [showPlacement, setShowPlacement] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [output, setOutput] = useState("");
  const [structured, setStructured] = useState(null);
  const [savedId, setSavedId] = useState(null);

  const params = {
    goal,
    current_level: level,
    hours_per_day: hours,
    format_preference: fmt,
    months,
    target_date: targetDate,
  };

  const finish = (id) => {
    localStorage.setItem("lp_onboarded", "1");
    if (id) setSavedId(id);
  };

  const skip = () => {
    localStorage.setItem("lp_onboarded", "1");
    navigate("/");
  };

  const next = () => {
    if (step === 0 && !goal.trim()) return;
    setStep((s) => Math.min(3, s + 1));
    setError("");
  };

  const back = () => {
    setError("");
    setStep((s) => Math.max(0, s - 1));
  };

  const generate = async () => {
    if (!goal.trim() || loading) return;
    setLoading(true);
    setError("");
    setOutput("");
    setStructured(null);
    setSavedId(null);
    try {
      if (mode === "structured") {
        const data = await pathStructured(params);
        if (data.error) setError(data.error);
        else {
          setStructured(data.output);
          finish(data.id);
        }
      } else {
        const full = await pathStream(params, (text) => setOutput(text));
        if (full) {
          const saved = await pathStreamSave({ ...params, output: full });
          finish(saved.id);
        }
      }
    } catch (e) {
      setError(e.message || "Generation failed.");
    }
    setLoading(false);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <Rocket size={28} />
        <div>
          <h2>Setup wizard</h2>
          <p className="subtitle">Four quick steps: goal, level, pace, then your first roadmap.</p>
        </div>
        <button className="btn-icon wizard-skip" onClick={skip}>
          <X size={14} /> Skip
        </button>
      </div>

      <div className="wizard-steps">
        {STEPS.map((label, i) => (
          <div key={label} className={`wizard-step ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}>
            <span className="wizard-num">{i < step ? <CheckCircle2 size={14} /> : i + 1}</span>
            <span>{label}</span>
          </div>
        ))}
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="wizard-card">
        {step === 0 && (
          <div className="wizard-body">
            <h3>What do you want to learn?</h3>
            <p className="subtitle">Be specific — the roadmap, flashcards and quizzes all key off this goal.</p>
            <textarea
              rows={3}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g., Learn Cloud Computing with AWS"
            />
            <div className="wizard-examples">
              {EXAMPLES.map((ex) => (
                <button key={ex} className="btn-icon" onClick={() => setGoal(ex)}>{ex}</button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="wizard-body">
            <h3>Where are you starting from?</h3>
            <p className="subtitle">Pick a level, or let a short placement test decide.</p>
            <div className="radio-group">
              {LEVELS.map((l) => (
                <label key={l} className={`radio-pill ${level === l ? "active" : ""}`}>
                  <input type="radio" name="level" checked={level === l} onChange={() => setLevel(l)} />
                  {l.charAt(0).toUpperCase() + l.slice(1)}
                </label>
              ))}
            </div>
            <button className="btn-secondary" onClick={() => setShowPlacement(true)} disabled={!goal.trim()}>
              <ClipboardCheck size={16} /> Take the 5-question placement test
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="wizard-body">
            <h3>How much time can you put in?</h3>
            <label>Hours per day: <strong>{hours}h</strong></label>
            <input type="range" min={1} max={12} value={hours} onChange={(e) => setHours(Number(e.target.value))} />
            <label>Timeline: <strong>{months} {months === 1 ? "month" : "months"}</strong></label>
            <input type="range" min={1} max={24} value={months} onChange={(e) => setMonths(Number(e.target.value))} />
            <label>Target completion date (optional)</label>
            <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
            <label>Preferred format</label>
            <select value={fmt} onChange={(e) => setFmt(e.target.value)}>
              {FORMATS.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-body">
            <h3>Generate your roadmap</h3>
            <p className="subtitle">
              {goal} · {level} · {hours}h/day · {months} months
            </p>
            <div className="radio-group">
              <label className={`radio-pill ${mode === "structured" ? "active" : ""}`}>
                <input type="radio" checked={mode === "structured"} onChange={() => setMode("structured")} />
                Interactive checklist
              </label>
              <label className={`radio-pill ${mode === "stream" ? "active" : ""}`}>
                <input type="radio" checked={mode === "stream"} onChange={() => setMode("stream")} />
                Live markdown
              </label>
            </div>
            <button className="btn-primary" onClick={generate} disabled={loading || !goal.trim()}>
              {loading ? <Loader2 className="spin" size={18} /> : <Wand2 size={16} />} Generate my path
            </button>

            {loading && !structured && !output && (
              <p className="saved-note">Working — the plan streams in below as it is written.</p>
            )}

            {structured && (
              <>
                <PathView format="structured" content={structured} />
                <div className="wizard-finish">
                  <Link className="btn-primary" to="/history" onClick={() => finish(savedId)}>
                    <ArrowRight size={16} /> Open in Path History
                  </Link>
                  <Link className="btn-secondary" to="/study" onClick={() => finish(savedId)}>
                    Go to Study Hub
                  </Link>
                </div>
              </>
            )}

            {output && (
              <>
                <div className="markdown-body">
                  <ReactMarkdown>{output}</ReactMarkdown>
                </div>
                {!loading && (
                  <div className="wizard-finish">
                    <Link className="btn-primary" to="/history" onClick={() => finish(savedId)}>
                      <ArrowRight size={16} /> Open in Path History
                    </Link>
                    <Link className="btn-secondary" to="/study" onClick={() => finish(savedId)}>
                      Go to Study Hub
                    </Link>
                  </div>
                )}
              </>
            )}

            {!structured && !output && !loading && (
              <p className="subtitle"><Zap size={14} /> You can change anything later and regenerate as a new version.</p>
            )}
          </div>
        )}

        <div className="wizard-nav">
          <button className="btn-secondary" onClick={back} disabled={step === 0 || loading}>
            <ArrowLeft size={16} /> Back
          </button>
          {step < 3 && (
            <button className="btn-primary" onClick={next} disabled={step === 0 && !goal.trim()}>
              Continue <ArrowRight size={16} />
            </button>
          )}
        </div>
      </div>

      {showPlacement && (
        <PlacementTest
          goal={goal}
          onClose={() => setShowPlacement(false)}
          onDone={(lvl) => {
            setLevel(lvl);
            setShowPlacement(false);
          }}
        />
      )}
    </div>
  );
}
