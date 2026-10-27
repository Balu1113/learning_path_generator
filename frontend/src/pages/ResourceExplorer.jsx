import { useState } from "react";
import { searchResources } from "../api/client";
import { Search, Filter, BookOpen } from "lucide-react";

const DOMAINS = [
  "", "web_development", "data_science", "cloud_devops",
  "mobile_development", "cybersecurity", "ai_ml_engineering", "blockchain",
];
const DIFFICULTIES = ["any", "beginner", "intermediate", "advanced"];

function formatDomain(d) {
  return d.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ResourceExplorer() {
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("");
  const [difficulty, setDifficulty] = useState("any");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    setLoading(true);
    setError("");
    setResults([]);
    try {
      const data = await searchResources({ query, domain, difficulty });
      if (data.error) setError(data.error);
      else setResults(data.results || []);
    } catch {
      setError("Failed to connect to backend.");
    }
    setLoading(false);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <BookOpen size={28} />
        <div>
          <h2>Resource Explorer</h2>
          <p className="subtitle">Browse and search the knowledge base of learning resources.</p>
        </div>
      </div>

      <div className="search-bar">
        <div className="search-field">
          <Search size={16} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search resources... (e.g., Python web framework, Docker)"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <div className="filter-group">
          <Filter size={16} />
          <select value={domain} onChange={(e) => setDomain(e.target.value)}>
            <option value="">All Domains</option>
            {DOMAINS.filter(Boolean).map((d) => (
              <option key={d} value={d}>{formatDomain(d)}</option>
            ))}
          </select>
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>{d === "any" ? "Any Level" : formatDomain(d)}</option>
            ))}
          </select>
          <button className="btn-primary" onClick={handleSearch} disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="results-grid">
        {results.map((r, i) => {
          const m = r.metadata;
          return (
            <div key={i} className="resource-card">
              <div className="card-top">
                <span className="difficulty-badge" data-level={m.difficulty}>{m.difficulty}</span>
                <span className="hours-badge">{m.estimated_hours}h</span>
                {m.verified && <span className="quality-badge verified">verified</span>}
                {m.stale && !m.broken && <span className="quality-badge stale">stale</span>}
                {m.broken && <span className="quality-badge broken">link down</span>}
                {m.cost && m.cost !== "free" && <span className="quality-badge cost">{m.cost}</span>}
                {m.rating != null && (
                  <span className="quality-badge rating">★ {Number(m.rating).toFixed(1)}</span>
                )}
              </div>
              {m.url ? (
                <h3><a href={m.url} target="_blank" rel="noreferrer">{m.topic_name}</a></h3>
              ) : (
                <h3>{m.topic_name}</h3>
              )}
              <p className="card-domain">{formatDomain(m.domain)} &rsaquo; {formatDomain(m.category || "")}</p>
              {m.description && <p className="card-desc">{m.description}</p>}
              <p className="card-source">
                {m.source === "catalog" ? "catalog" : "ai suggestion"}
                {m.content_source === "curated" ? " · curated" : ""}
              </p>
            </div>
          );
        })}
      </div>

      {!loading && results.length === 0 && !error && (
        <div className="empty-state">
          <Search size={48} />
          <p>Search for topics, skills, or technologies to explore available resources.</p>
        </div>
      )}
    </div>
  );
}
