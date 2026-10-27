import { useEffect, useState } from "react";
import { Code2, Play, Send, CheckCircle2, XCircle, Loader2, Trophy, Sparkles } from "lucide-react";
import { getChallenges, getChallenge, runChallenge, submitChallenge, getLeaderboard, generateCodeChallenges } from "../api/client";

const LANGUAGE_COLORS = {
  python: "#3776ab",
  javascript: "#f7df1e",
  java: "#007396",
  cpp: "#00599c",
  csharp: "#239120",
  sql: "#336791",
  go: "#00add8",
  rust: "#ce422b",
};

export default function CodeChallengePanel({ pathId, phaseIdx, phaseTitle }) {
  const [challenges, setChallenges] = useState([]);
  const [selected, setSelected] = useState(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [genLanguage, setGenLanguage] = useState("python");
  const [genDifficulty, setGenDifficulty] = useState("medium");

  useEffect(() => {
    loadChallenges();
  }, [pathId, phaseIdx]);

  const loadChallenges = () => {
    getChallenges(pathId, phaseIdx)
      .then((d) => {
        if (!d.error) {
          setChallenges(d.challenges || []);
          if (d.challenges?.length) setSelected(d.challenges[0]);
          else setShowGenerate(true);
        }
      })
      .catch(() => {});
  };

  useEffect(() => {
    if (!selected) return;
    getChallenge(selected.id)
      .then((d) => {
        if (!d.error) {
          setCode(d.starter_code || "");
          if (d.submission?.code) setCode(d.submission.code);
        }
      })
      .catch(() => {});
  }, [selected]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const data = await generateCodeChallenges(pathId, phaseIdx, {
        language: genLanguage,
        difficulty: genDifficulty,
        count: 3,
      });
      if (data.error) {
        setError(data.error);
      } else {
        setShowGenerate(false);
        loadChallenges();
      }
    } catch (e) {
      setError("Generation failed");
    }
    setGenerating(false);
  };

  const handleRun = async () => {
    if (!selected || !code.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await runChallenge(selected.id, code);
      if (data.error) setError(data.error);
      else setResults(data);
    } catch (e) {
      setError("Run failed");
    }
    setLoading(false);
  };

  const handleSubmit = async () => {
    if (!selected || !results) return;
    setLoading(true);
    try {
      const data = await submitChallenge(selected.id);
      if (!data.error) {
        setSelected({ ...selected, user_status: data.status, user_score: data.score });
        getLeaderboard(pathId, phaseIdx)
          .then((d) => setLeaderboard(d.leaderboard || []))
          .catch(() => {});
      }
    } catch (e) {
      setError("Submit failed");
    }
    setLoading(false);
  };

  if (!challenges.length) {
    return (
      <div className="study-card">
        <div className="study-card-title"><Code2 size={17} /> Code Challenges</div>
        {showGenerate ? (
          <div className="challenge-generate-form">
            <p className="subtitle">No challenges yet. Generate some with AI.</p>
            <div className="form-group">
              <label>Language</label>
              <select value={genLanguage} onChange={(e) => setGenLanguage(e.target.value)}>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
                <option value="csharp">C#</option>
                <option value="sql">SQL</option>
                <option value="go">Go</option>
                <option value="rust">Rust</option>
              </select>
            </div>
            <div className="form-group">
              <label>Difficulty</label>
              <select value={genDifficulty} onChange={(e) => setGenDifficulty(e.target.value)}>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            {error && <div className="error-box">{error}</div>}
            <button className="btn-primary" onClick={handleGenerate} disabled={generating}>
              {generating ? <Loader2 className="spin" size={16} /> : <Sparkles size={16} />}
              {generating ? "Generating..." : "Generate Challenges"}
            </button>
          </div>
        ) : (
          <p className="subtitle">No challenges available for this phase.</p>
        )}
      </div>
    );
  }

  return (
    <div className="code-challenge-panel">
      <div className="study-card">
        <div className="study-card-head">
          <div className="study-card-title"><Code2 size={17} /> Code Challenges</div>
          <button className="btn-secondary" onClick={() => setShowGenerate(!showGenerate)}>
            <Sparkles size={14} /> Generate More
          </button>
        </div>
        
        {showGenerate && (
          <div className="challenge-generate-form">
            <div className="form-group">
              <label>Language</label>
              <select value={genLanguage} onChange={(e) => setGenLanguage(e.target.value)}>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
                <option value="csharp">C#</option>
                <option value="sql">SQL</option>
                <option value="go">Go</option>
                <option value="rust">Rust</option>
              </select>
            </div>
            <div className="form-group">
              <label>Difficulty</label>
              <select value={genDifficulty} onChange={(e) => setGenDifficulty(e.target.value)}>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            {error && <div className="error-box">{error}</div>}
            <button className="btn-primary" onClick={handleGenerate} disabled={generating}>
              {generating ? <Loader2 className="spin" size={16} /> : <Sparkles size={16} />}
              {generating ? "Generating..." : "Generate"}
            </button>
          </div>
        )}
        
        <div className="challenge-list">
          {challenges.map((c) => (
            <button
              key={c.id}
              className={`challenge-item ${selected?.id === c.id ? "active" : ""} ${c.user_status === "passed" ? "passed" : ""}`}
              onClick={() => setSelected(c)}
            >
              <div className="challenge-header">
                <strong>{c.title}</strong>
                {c.user_status === "passed" && <CheckCircle2 size={14} className="passed-icon" />}
              </div>
              <div className="challenge-meta">
                <span className="difficulty" data-level={c.difficulty}>{c.difficulty}</span>
                <span className="language" style={{ backgroundColor: LANGUAGE_COLORS[c.language] }}>
                  {c.language}
                </span>
                <span className="points">{c.points} pts</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {selected && (
        <div className="study-card challenge-detail">
          <div className="study-card-head">
            <div>
              <div className="study-card-title">{selected.title}</div>
              <div className="study-card-sub">{selected.description}</div>
            </div>
          </div>

          <div className="code-editor-wrap">
            <textarea
              className="code-editor"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Write your code here..."
              spellCheck="false"
            />
          </div>

          <div className="challenge-actions">
            <button className="btn-primary" onClick={handleRun} disabled={loading || !code.trim()}>
              {loading ? <Loader2 className="spin" size={16} /> : <Play size={16} />} Run Tests
            </button>
            {results && results.passed_tests === results.total_tests && selected.user_status !== "passed" && (
              <button className="btn-success" onClick={handleSubmit} disabled={loading}>
                <Send size={16} /> Submit
              </button>
            )}
          </div>

          {error && <div className="error-box">{error}</div>}

          {results && (
            <div className="test-results">
              <div className="results-header">
                <span className="results-title">Test Results</span>
                <span className={`results-score ${results.passed_tests === results.total_tests ? "passed" : "failed"}`}>
                  {results.passed_tests}/{results.total_tests} passed
                </span>
              </div>
              <div className="test-cases">
                {results.test_results.map((t, i) => (
                  <div key={i} className={`test-case ${t.passed ? "passed" : "failed"}`}>
                    <div className="test-case-header">
                      {t.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                      <span>Test {i + 1}</span>
                    </div>
                    {!t.passed && (
                      <div className="test-case-details">
                        <div><strong>Input:</strong> <code>{t.input}</code></div>
                        <div><strong>Expected:</strong> <code>{t.expected}</code></div>
                        <div><strong>Got:</strong> <code>{t.actual}</code></div>
                        {t.error && <div><strong>Error:</strong> {t.error}</div>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {leaderboard.length > 0 && (
        <div className="study-card leaderboard-card">
          <div className="study-card-title"><Trophy size={17} /> Leaderboard</div>
          <div className="leaderboard-list">
            {leaderboard.map((entry, i) => (
              <div key={i} className="leaderboard-entry">
                <span className="rank">#{i + 1}</span>
                <span className="username">{entry.username}</span>
                <span className="score">{entry.score} pts</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
