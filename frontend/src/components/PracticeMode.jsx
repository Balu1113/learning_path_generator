import { useState, useEffect, useRef } from "react";
import { practiceTurn, getPathHistory } from "../api/client";
import { Loader2, MessageSquare, Send, X } from "lucide-react";

const SCENARIOS = [
  { id: "mock_interview", label: "Mock Interview", desc: "Practice answering technical questions." },
  { id: "debugging", label: "Debugging Session", desc: "Work through a bug with guided questions." },
  { id: "code_review", label: "Code Review", desc: "Explain your code and get feedback." },
  { id: "architecture", label: "Architecture Review", desc: "Design a system and discuss trade-offs." },
  { id: "stakeholder", label: "Stakeholder Chat", desc: "Explain a concept to a non-technical audience." },
];

export default function PracticeMode({ pathId, onClose }) {
  const [scenario, setScenario] = useState("mock_interview");
  const [started, setStarted] = useState(false);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    if (bottomRef.current) bottomRef.current.scrollIntoView({ behavior: "smooth" });
  }, [history, reply]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const msg = input.trim();
    setInput("");
    setLoading(true);
    setError("");
    try {
      const d = await practiceTurn(pathId, scenario, msg, history);
      if (d.error) setError(d.error);
      else {
        setHistory((h) => [...h, { role: "human", content: msg }, { role: "assistant", content: d.reply }]);
        setReply(d.reply);
      }
    } catch {
      setError("Practice session failed.");
    }
    setLoading(false);
  };

  const start = () => {
    setStarted(true);
    setHistory([{ role: "assistant", content: `Let's begin the ${SCENARIOS.find(s => s.id === scenario)?.label}. I'll ask you questions or present scenarios — answer as you would in a real setting. What would you like to start with?` }]);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3><MessageSquare size={18} /> AI Practice Mode</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        {!started ? (
          <div className="modal-body">
            <p className="subtitle">Choose a practice scenario to sharpen your skills.</p>
            <div className="scenario-grid">
              {SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  className={`scenario-card ${scenario === s.id ? "active" : ""}`}
                  onClick={() => setScenario(s.id)}
                >
                  <strong>{s.label}</strong>
                  <small>{s.desc}</small>
                </button>
              ))}
            </div>
            <button className="btn-primary" onClick={start}>
              Start {SCENARIOS.find((s) => s.id === scenario)?.label}
            </button>
          </div>
        ) : (
          <div className="modal-body practice-chat">
            <div className="practice-messages">
              {history.map((msg, i) => (
                <div key={i} className={`practice-msg ${msg.role}`}>
                  <strong>{msg.role === "human" ? "You" : "Coach"}</strong>
                  <p>{msg.content}</p>
                </div>
              ))}
              {loading && <div className="practice-msg assistant loading"><Loader2 className="spin" size={16} /> Thinking...</div>}
              <div ref={bottomRef} />
            </div>
            {error && <div className="error-box">{error}</div>}
            <div className="practice-input">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your answer..."
                onKeyDown={(e) => e.key === "Enter" && send()}
                disabled={loading}
              />
              <button className="btn-primary" onClick={send} disabled={loading || !input.trim()}>
                <Send size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}