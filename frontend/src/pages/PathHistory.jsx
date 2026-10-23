import { useEffect, useState } from "react";
import { getPathHistory, deletePath, sendFeedback, icsUrl, ankiUrl, notionUrl, regeneratePath } from "../api/client";
import {
  History, Trash2, Loader2, ThumbsUp, ThumbsDown, Download,
  RefreshCw, GitCompare, Printer, Share2,
} from "lucide-react";
import PathView from "../components/PathView";
import ChatPanel from "../components/ChatPanel";
import ShareModal from "../components/ShareModal";

function formatDate(ts) {
  const t = Number(ts);
  if (!t) return "";
  return new Date(t * 1000).toLocaleString();
}

function downloadMarkdown(p) {
  let text = p.content;
  if (p.format === "structured") {
    try {
      const s = JSON.parse(p.content);
      text = `# ${s.title}\n\n${s.summary || ""}\n\n` + (s.phases || [])
        .map((ph, i) => `## Phase ${i + 1}: ${ph.title} (${ph.estimated_weeks || "?"} weeks)\n\n${ph.description || ""}\n\n` +
          (ph.topics || []).map((t) => `### ${t.title}\n\n${t.details || ""}\n\n` +
            (t.resources || []).map((r) => `- **${r.name}** (${r.type || "resource"})${r.note ? ` — ${r.note}` : ""}`).join("\n")
          ).join("\n\n"))
        .join("\n\n");
    } catch {
      text = p.content;
    }
  }
  const blob = new Blob([text], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${p.goal.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "path"}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function PathHistory() {
  const [paths, setPaths] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [feedbackState, setFeedbackState] = useState({});
  const [regenerating, setRegenerating] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [compareId, setCompareId] = useState("");
  const [shareOpen, setShareOpen] = useState(false);

  const load = (selectId) => {
    setLoading(true);
    getPathHistory()
      .then((d) => {
        if (d.error) setError(d.error);
        else {
          const list = d.paths || [];
          setPaths(list);
          setSelected((prev) => {
            if (selectId) return list.find((p) => p.id === selectId) || prev || list[0] || null;
            if (!prev) return list[0] || null;
            return list.find((p) => p.id === prev.id) || null;
          });
        }
      })
      .catch(() => setError("Failed to load history"))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  useEffect(() => {
    setShareOpen(false);
  }, [selected?.id]);

  const versions = selected
    ? paths.filter((p) => p.lineage === selected.lineage).sort((a, b) => a.version - b.version)
    : [];
  const compareTarget = versions.find((v) => v.id === compareId && v.id !== selected?.id)
    || versions.filter((v) => v.id !== selected?.id).slice(-1)[0]
    || null;

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this saved path?")) return;
    try {
      const d = await deletePath(id);
      if (d.error) {
        setError(d.error);
        return;
      }
      setPaths((prev) => prev.filter((p) => p.id !== id));
      setSelected((prev) => (prev?.id === id ? null : prev));
    } catch {
      setError("Failed to delete path");
    }
  };

  const handleFeedback = async (id, value) => {
    try {
      const d = await sendFeedback(id, value);
      if (d.error) setError(d.error);
      else setFeedbackState((prev) => ({ ...prev, [id]: { ...prev[id], mine: value } }));
    } catch {
      setError("Failed to save feedback");
    }
  };

  const handleRegenerate = async () => {
    if (!selected || regenerating) return;
    setRegenerating(true);
    setError("");
    try {
      const d = await regeneratePath(selected.id);
      if (d.error) {
        setError(d.error);
      } else {
        setCompareMode(false);
        load(d.id);
      }
    } catch {
      setError("Regeneration failed — the model could not be reached.");
    }
    setRegenerating(false);
  };

  const lineageCount = paths.filter((p) => p.lineage === selected?.lineage).length;

  return (
    <div className="page-container">
      <div className="page-header">
        <History size={28} />
        <div>
          <h2>Path History</h2>
          <p className="subtitle">Previously generated learning paths, newest first. Click one to view it.</p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loading ? (
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Loading saved paths...</p>
        </div>
      ) : paths.length === 0 && !error ? (
        <div className="empty-state">
          <History size={48} />
          <p>No saved paths yet. Generate one in Agent Mode or Quick Path.</p>
        </div>
      ) : (
        <div className="form-grid">
          <div className="form-left history-list">
            {paths.map((p) => (
              <div
                key={p.id}
                className={`history-item ${selected?.id === p.id ? "active" : ""}`}
                onClick={() => setSelected(p)}
              >
                <div className="history-item-info">
                  <strong>{p.goal}</strong>
                  <span className="history-meta">
                    {formatDate(p.created_at)}
                    {p.version > 1 && ` · v${p.version}`}
                    {p.current_level && ` · ${p.current_level}`}
                    {p.hours_per_day && ` · ${p.hours_per_day}h/day`}
                    {p.months && ` · ${p.months} months`}
                    {p.source === "quick" ? " · Quick Path" : " · Agent"}
                  </span>
                </div>
                <button
                  className="history-delete"
                  title="Delete path"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(p.id);
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>

          <div className="form-right">
            {selected && (
              <>
                <div className="path-toolbar">
                  <button className="btn-icon" title="Download .md" onClick={() => downloadMarkdown(selected)}>
                    <Download size={16} /> .md
                  </button>
                  <a className="btn-icon" title="Export calendar" href={icsUrl(selected.id)} download>
                    <Download size={16} /> .ics
                  </a>
                  <a className="btn-icon" title="Export as Anki CSV" href={ankiUrl(selected.id)} download>
                    <Download size={16} /> Anki
                  </a>
                  <a className="btn-icon" title="Notion-ready markdown" href={notionUrl(selected.id)} download>
                    <Download size={16} /> Notion
                  </a>
                  <button className="btn-icon" title="Print / save as PDF" onClick={() => window.print()}>
                    <Printer size={16} /> Print
                  </button>
                  <button
                    className="btn-icon"
                    title="Create a public read-only link"
                    onClick={() => setShareOpen(true)}
                  >
                    <Share2 size={16} /> Share
                  </button>
                  <button className="btn-icon" title="Regenerate this roadmap as a new version" onClick={handleRegenerate} disabled={regenerating}>
                    {regenerating ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />} Regenerate
                  </button>
                  <button
                    className={`btn-icon ${compareMode ? "active" : ""}`}
                    title="Compare versions side by side"
                    onClick={() => setCompareMode((m) => !m)}
                    disabled={lineageCount < 2}
                  >
                    <GitCompare size={16} /> Compare
                  </button>
                  <div className="feedback-group">
                    <button
                      className={`btn-icon ${feedbackState[selected.id]?.mine === 1 ? "active" : ""}`}
                      title="Good path"
                      onClick={() => handleFeedback(selected.id, 1)}
                    >
                      <ThumbsUp size={16} />
                    </button>
                    <button
                      className={`btn-icon ${feedbackState[selected.id]?.mine === -1 ? "active" : ""}`}
                      title="Bad path"
                      onClick={() => handleFeedback(selected.id, -1)}
                    >
                      <ThumbsDown size={16} />
                    </button>
                  </div>
                </div>

                {versions.length > 1 && (
                  <div className="version-row">
                    <span className="version-label">Versions:</span>
                    {versions.map((v) => (
                      <button
                        key={v.id}
                        className={`version-chip ${v.id === selected.id ? "active" : ""}`}
                        onClick={() => setSelected(v)}
                        title={`Created ${formatDate(v.created_at)}`}
                      >
                        v{v.version}
                      </button>
                    ))}
                    <span className="version-note">Regenerating keeps every earlier version.</span>
                  </div>
                )}

                {compareMode ? (
                  <div className="compare-controls">
                    <span className="version-label">Comparing v{selected.version} with</span>
                    <select value={compareTarget?.id || ""} onChange={(e) => setCompareId(e.target.value)}>
                      {versions.filter((v) => v.id !== selected.id).map((v) => (
                        <option key={v.id} value={v.id}>
                          v{v.version} · {formatDate(v.created_at)}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}

                {compareMode && compareTarget ? (
                  <div className="compare-grid">
                    <div className="compare-col">
                      <div className="compare-head">v{selected.version}</div>
                      <PathView pathId={selected.id} format={selected.format} content={selected.content} hoursPerDay={selected.hours_per_day} onVersionCreated={load} />
                    </div>
                    <div className="compare-col">
                      <div className="compare-head">v{compareTarget.version}</div>
                      <PathView pathId={compareTarget.id} format={compareTarget.format} content={compareTarget.content} hoursPerDay={compareTarget.hours_per_day} onVersionCreated={load} />
                    </div>
                  </div>
                ) : (
                  <>
                    <PathView pathId={selected.id} format={selected.format} content={selected.content} hoursPerDay={selected.hours_per_day} onVersionCreated={load} />
                    <ChatPanel pathId={selected.id} />
                  </>
                )}
              </>
            )}
            {shareOpen && selected && (
              <ShareModal pathId={selected.id} onClose={() => setShareOpen(false)} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
