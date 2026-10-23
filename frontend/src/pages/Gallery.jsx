import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getGallery } from "../api/client";
import { Eye, Library, Loader2, Search } from "lucide-react";

const FORMAT_FILTERS = [
  { key: "all", label: "All" },
  { key: "structured", label: "Interactive" },
  { key: "markdown", label: "Markdown" },
];

function formatDate(raw) {
  const n = Number(raw);
  if (Number.isFinite(n) && n > 0) return new Date(n * 1000).toLocaleDateString();
  const s = String(raw || "");
  return s.length >= 10 ? s.slice(0, 10) : "";
}

export default function Gallery() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [format, setFormat] = useState("all");

  useEffect(() => {
    getGallery()
      .then((d) => {
        if (d.error) setError(d.error);
        else setItems(d.items || []);
      })
      .catch(() => setError("Failed to load the gallery."));
  }, []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (items || []).filter((it) => {
      if (format !== "all" && it.format !== format) return false;
      if (!q) return true;
      return [it.goal, it.title, it.summary]
        .filter(Boolean)
        .some((s) => s.toLowerCase().includes(q));
    });
  }, [items, query, format]);

  if (error) {
    return (
      <div className="page-container">
        <div className="error-box">{error}</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Library size={28} />
        <div>
          <h2>Path Gallery</h2>
          <p className="subtitle">Roadmaps learners chose to share publicly. Open one read-only.</p>
        </div>
      </div>

      <div className="gallery-toolbar">
        <div className="gallery-search">
          <Search size={15} />
          <input
            type="text"
            placeholder="Search goals, titles or summaries…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="gallery-filters">
          {FORMAT_FILTERS.map((f) => (
            <button
              key={f.key}
              className={`btn-icon ${format === f.key ? "active" : ""}`}
              onClick={() => setFormat(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {items === null ? (
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Loading gallery…</p>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Library size={48} />
          <p>Nothing shared yet. Use <strong>Share</strong> on a roadmap in Path History to
            publish it here for anyone to browse.</p>
        </div>
      ) : visible.length === 0 ? (
        <div className="empty-state">
          <Search size={48} />
          <p>No shared roadmaps match your filters.</p>
        </div>
      ) : (
        <div className="gallery-grid">
          {visible.map((it) => (
            <Link key={it.slug} to={`/p/${it.slug}`} className="gallery-card">
              <div className="gallery-card-top">
                <span className={`gallery-format ${it.format}`}>
                  {it.format === "structured" ? "Interactive" : "Markdown"}
                </span>
                <Eye size={14} />
              </div>
              <h3>{it.title || it.goal}</h3>
              {it.title && it.goal && it.title !== it.goal && (
                <p className="gallery-goal">{it.goal}</p>
              )}
              {it.summary && <p className="gallery-summary">{it.summary}</p>}
              <div className="gallery-meta">
                {it.phase_count > 0 && <span>{it.phase_count} phases</span>}
                {it.topic_count > 0 && <span>{it.topic_count} topics</span>}
                {it.hours_per_day && <span>{it.hours_per_day}h/day</span>}
                {it.months && <span>{it.months} months</span>}
                {it.created_at && <span>{formatDate(it.created_at)}</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
