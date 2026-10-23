import { useState } from "react";
import { pathStructured, pathStream, pathStreamSave } from "../api/client";
import ReactMarkdown from "react-markdown";
import { Zap, Loader2, ClipboardCheck } from "lucide-react";
import PathView from "../components/PathView";
import PlacementTest from "../components/PlacementTest";

const LEVELS = ["beginner", "intermediate", "advanced"];
const FORMATS = [
  "courses and hands-on projects",
  "books and documentation",
  "video tutorials",
  "mix of all formats",
];

export default function QuickPath() {
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("beginner");
  const [hours, setHours] = useState(2);
  const [months, setMonths] = useState(6);
  const [targetDate, setTargetDate] = useState("");
  const [mode, setMode] = useState("stream");
  const [fmt, setFmt] = useState(FORMATS[0]);
  const [output, setOutput] = useState("");
  const [structured, setStructured] = useState(null);
  const [savedId, setSavedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPlacement, setShowPlacement] = useState(false);

  const params = {
    goal,
    current_level: level,
    hours_per_day: hours,
    format_preference: fmt,
    months,
    target_date: targetDate,
  };

  const handleGenerate = async () => {
    if (!goal.trim()) return;
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
          setSavedId(data.id);
        }
      } else {
        const full = await pathStream(params, (text) => setOutput(text));
        if (full) {
          const saved = await pathStreamSave({ ...params, output: full });
          setSavedId(saved.id);
        }
      }
    } catch (e) {
      setError(e.message || "Failed to generate.");
    }
    setLoading(false);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <Zap size={28} />
        <div>
          <h2>Quick Path Generator</h2>
          <p className="subtitle">Generate a learning path with the LangChain chain. Stream it live, or build an interactive checklist roadmap.</p>
        </div>
      </div>

      <div className="form-grid">
        <div className="form-left">
          <label>Learning Goal</label>
          <textarea
            rows={3}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g., Learn Cloud Computing with AWS"
          />

          <button className="btn-secondary" onClick={() => setShowPlacement(true)} disabled={!goal.trim()}>
            <ClipboardCheck size={16} /> Not sure of your level? Take the placement test
          </button>

          <label>Current Level</label>
          <div className="radio-group">
            {LEVELS.map((l) => (
              <label key={l} className={`radio-pill ${level === l ? "active" : ""}`}>
                <input type="radio" name="level" value={l} checked={level === l} onChange={() => setLevel(l)} />
                {l.charAt(0).toUpperCase() + l.slice(1)}
              </label>
            ))}
          </div>

          <label>Hours per Day: <strong>{hours}h</strong></label>
          <input
            type="range"
            min={1}
            max={12}
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
          />

          <label>How Many Months: <strong>{months} {months === 1 ? "month" : "months"}</strong></label>
          <input
            type="range"
            min={1}
            max={24}
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
          />

          <label>Target Completion Date (optional)</label>
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
          />

          <label>Preferred Format</label>
          <select value={fmt} onChange={(e) => setFmt(e.target.value)}>
            {FORMATS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>

          <label>Output Mode</label>
          <div className="radio-group">
            <label className={`radio-pill ${mode === "stream" ? "active" : ""}`}>
              <input type="radio" name="mode" checked={mode === "stream"} onChange={() => setMode("stream")} />
              Live markdown
            </label>
            <label className={`radio-pill ${mode === "structured" ? "active" : ""}`}>
              <input type="radio" name="mode" checked={mode === "structured"} onChange={() => setMode("structured")} />
              Interactive checklist
            </label>
          </div>

          <button className="btn-primary" onClick={handleGenerate} disabled={loading || !goal.trim()}>
            {loading ? <Loader2 className="spin" size={18} /> : "Generate Path"}
          </button>
        </div>

        <div className="form-right">
          {error && <div className="error-box">{error}</div>}
          {structured && (
            <>
              <PathView pathId={savedId} format="structured" content={structured} />
              <p className="saved-note">Saved to Path History</p>
            </>
          )}
          {output && (
            <>
              <div className="markdown-body">
                <ReactMarkdown>{output}</ReactMarkdown>
              </div>
              {loading ? (
                <p className="saved-note">Streaming... will save when complete</p>
              ) : (
                <p className="saved-note">Saved to Path History</p>
              )}
            </>
          )}
          {!output && !structured && !error && !loading && (
            <div className="empty-state">
              <Zap size={48} />
              <p>Your generated learning path will appear here.</p>
            </div>
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
