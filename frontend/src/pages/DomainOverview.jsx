import { useState, useEffect } from "react";
import { getDomains, getDomainTopics } from "../api/client";
import { Layers, ArrowRight, Loader2 } from "lucide-react";

export default function DomainOverview() {
  const [domains, setDomains] = useState([]);
  const [selected, setSelected] = useState(null);
  const [topics, setTopics] = useState([]);
  const [loadingDomains, setLoadingDomains] = useState(true);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getDomains()
      .then((d) => {
        if (d.error) setError(d.error);
        else setDomains(d.domains || []);
      })
      .catch(() => setError("Failed to load domains"))
      .finally(() => setLoadingDomains(false));
  }, []);

  const loadDomain = async (domain) => {
    setSelected(domain);
    setLoadingTopics(true);
    setTopics([]);
    try {
      const data = await getDomainTopics(domain.name);
      if (data.error) setError(data.error);
      else setTopics(data.topics || []);
    } catch {
      setError("Failed to load topics");
    }
    setLoadingTopics(false);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <Layers size={28} />
        <div>
          <h2>Domain Overview</h2>
          <p className="subtitle">AI-generated learning domains and topics. Click any domain to explore.</p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loadingDomains ? (
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Generating domains via Gemini...</p>
        </div>
      ) : (
        <div className="domains-grid">
          {domains.map((d, i) => (
            <button
              key={i}
              className={`domain-card ${selected?.name === d.name ? "active" : ""}`}
              onClick={() => loadDomain(d)}
            >
              <h3>{d.label || d.name}</h3>
              <p>{d.description}</p>
              <ArrowRight size={16} className="arrow-icon" />
            </button>
          ))}
        </div>
      )}

      {loadingTopics && (
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Generating topics for {selected?.label}...</p>
        </div>
      )}

      {topics.length > 0 && !loadingTopics && (
        <div className="topics-section">
          <h3>{selected?.label || selected?.name}</h3>
          <div className="topics-list">
            {topics.map((t, i) => (
              <div key={i} className="topic-item">
                <strong>{t.name}</strong>
                <p className="topic-resources">{t.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
