import { useState, useRef, useEffect } from "react";
import { chatWithPath, socraticChat } from "../api/client";
import { Send, Loader2, MessageCircleQuestion, MessagesSquare } from "lucide-react";

const MODES = [
  { id: "coach", label: "Coach", Icon: MessagesSquare, placeholder: "Ask a question about this roadmap..." },
  { id: "socratic", label: "Socratic", Icon: MessageCircleQuestion, placeholder: "Answer the tutor's questions... it won't give you the answer" },
];

export default function ChatPanel({ pathId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("coach");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    const message = input.trim();
    if (!message || loading) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const call = mode === "socratic" ? socraticChat : chatWithPath;
      const d = await call(pathId, message, history);
      if (d.error) setError(d.error);
      else setMessages((prev) => [...prev, { role: "assistant", content: d.reply }]);
    } catch {
      setError(mode === "socratic" ? "The tutor is unavailable right now." : "Failed to reach the coach.");
    }
    setLoading(false);
  };

  const active = MODES.find((m) => m.id === mode) || MODES[0];

  return (
    <div className="chat-panel">
      <div className="chat-head">
        <h4>{mode === "socratic" ? "Socratic tutor" : "Ask about this path"}</h4>
        <div className="chat-mode-toggle">
          {MODES.map(({ id, label, Icon }) => (
            <button
              key={id}
              className={`mode-btn ${mode === id ? "active" : ""}`}
              onClick={() => setMode(id)}
              title={id === "socratic" ? "It only asks questions — never answers" : "Straight answers from your roadmap"}
            >
              <Icon size={13} /> {label}
            </button>
          ))}
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-empty">
            {mode === "socratic"
              ? "The tutor opens with a question about your roadmap. Answer it — it will only respond with the next question."
              : 'e.g. "Which topic should I start with this week?"'}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {loading && <div className="chat-msg assistant typing"><Loader2 className="spin" size={14} /></div>}
        <div ref={bottomRef} />
      </div>
      {error && <div className="error-box">{error}</div>}
      <div className="chat-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={active.placeholder}
          disabled={loading}
        />
        <button className="btn-primary chat-send" onClick={send} disabled={loading || !input.trim()}>
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
