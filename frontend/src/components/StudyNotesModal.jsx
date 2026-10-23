import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { generateStudyNotes } from "../api/client";
import { BookOpen, Loader2, Plus, X } from "lucide-react";

export default function StudyNotesModal({ pathId, phaseIdx, topicIdx, topicTitle, onClose }) {
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasMore, setHasMore] = useState(true);
  const depthRef = useRef(0);

  const fetchNext = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const d = await generateStudyNotes(pathId, {
        phase_idx: phaseIdx,
        topic_idx: topicIdx,
        depth: depthRef.current + 1,
      });
      if (d.error) {
        setError(d.error);
      } else {
        depthRef.current = d.depth;
        setSections((prev) => [...prev, d.section]);
        setHasMore(Boolean(d.has_more));
      }
    } catch {
      setError("Failed to load study notes. Check your connection and try again.");
    }
    setLoading(false);
  }, [pathId, phaseIdx, topicIdx, loading]);

  useEffect(() => {
    fetchNext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box ws-notes-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3><BookOpen size={16} /> Study notes — {topicTitle}</h3>
          <button className="modal-close" onClick={onClose} title="Close"><X size={18} /></button>
        </div>

        <div className="modal-body ws-notes-body">
          {sections.map((md, i) => (
            <article key={i} className={`markdown-body ws-notes-section ${i > 0 ? "deeper" : ""}`}>
              {i > 0 && <span className="ws-notes-level">Deep dive {i + 1}</span>}
              <ReactMarkdown>{md}</ReactMarkdown>
            </article>
          ))}

          {error && <div className="error-box">{error}</div>}

          {loading && (
            <div className="empty-state small">
              <Loader2 className="spin" size={24} />
              <p>{sections.length ? "Writing the next deep dive..." : "Writing your study notes..."}</p>
            </div>
          )}

          {!loading && hasMore && sections.length > 0 && (
            <button className="btn-secondary ws-notes-more" onClick={fetchNext}>
              <Plus size={15} /> Go deeper — more insights &amp; practice
            </button>
          )}

          {!loading && !hasMore && sections.length > 0 && (
            <p className="ws-notes-end">
              You have reached the deepest level for this topic. Mark it done, take the phase
              test, or move on to the next topic.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
