import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { agentGenerate, getPathHistory } from "../api/client";
import ReactMarkdown from "react-markdown";
import { Brain, Loader2, ChevronRight, Rocket, Wrench } from "lucide-react";

export default function AgentMode() {
  const navigate = useNavigate();
  const [goal, setGoal] = useState("");
  const [output, setOutput] = useState("");
  const [steps, setSteps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showWizardLink, setShowWizardLink] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("lp_onboarded")) return;
    let cancelled = false;
    getPathHistory()
      .then((d) => {
        if (cancelled) return;
        if (!(d.paths || []).length) navigate("/onboarding", { replace: true });
        else setShowWizardLink(true);
      })
      .catch(() => setShowWizardLink(true));
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const handleGenerate = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError("");
    setOutput("");
    setSteps([]);
    try {
      const data = await agentGenerate(goal);
      if (data.error) {
        setError(data.error);
      } else {
        setOutput(data.output);
        setSteps(data.steps || []);
      }
    } catch {
      setError("Failed to connect to backend. Make sure the server is running.");
    }
    setLoading(false);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <Brain size={28} />
        <div>
          <h2>Agent Mode (ReAct)</h2>
          <p className="subtitle">
            The ReAct agent reasons step-by-step, searches the knowledge base, estimates timelines, and generates a roadmap.
          </p>
        </div>
      </div>

      {showWizardLink && (
        <div className="wizard-banner">
          <Rocket size={16} />
          <span>First time here? The setup wizard builds your first roadmap in four steps.</span>
          <Link to="/onboarding" className="btn-icon">Open wizard <ChevronRight size={14} /></Link>
        </div>
      )}

      <div className="input-section">
        <div className="input-row">
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g., Become a Full Stack Web Developer, Learn Machine Learning, Get into Cybersecurity..."
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          />
          <button className="btn-primary" onClick={handleGenerate} disabled={loading || !goal.trim()}>
            {loading ? <Loader2 className="spin" size={18} /> : "Generate Roadmap"}
          </button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {steps.length > 0 && (
        <div className="agent-steps">
          <h3><Wrench size={18} /> Agent Thinking Process</h3>
          <div className="steps-list">
            {steps.map((s, i) => (
              <div key={i} className="step-card">
                <div className="step-header">
                  <span className="step-badge">Step {i + 1}</span>
                  <code className="tool-name">{s.tool}</code>
                </div>
                <div className="step-input">
                  <ChevronRight size={14} />
                  <span>{typeof s.input === "string" ? s.input : JSON.stringify(s.input)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {output && (
        <div className="output-section">
          <h3>Learning Roadmap</h3>
          <div className="markdown-body">
            <ReactMarkdown>{output}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
