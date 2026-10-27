import { useState, useEffect } from "react";
import { getPathHistory } from "../api/client";
import AnalyticsDashboard from "../components/AnalyticsDashboard";
import "../components/Layout.css";

export default function Analytics() {
  const [paths, setPaths] = useState([]);
  const [pathId, setPathId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getPathHistory()
      .then((d) => {
        const list = d.paths || [];
        setPaths(list);
        if (list.length) {
          const saved = localStorage.getItem("analytics:path");
          const pick = list.find((p) => p.id === saved) ? saved : list[0].id;
          setPathId(pick);
        }
      })
      .catch(() => setError("Failed to load your paths."));
  }, []);

  return (
    <div className="page-container">
      <h1>Learning Analytics</h1>

      {error && <div className="analytics-banner error">{error}</div>}

      {!error && paths.length === 0 && (
        <div className="analytics-banner empty">
          No learning paths yet. Generate a path first — your analytics will appear here.
        </div>
      )}

      {paths.length > 0 && (
        <>
          <div className="analytics-picker">
            <label htmlFor="analytics-path">Analyzing path:</label>
            <select
              id="analytics-path"
              value={pathId}
              onChange={(e) => {
                setPathId(e.target.value);
                localStorage.setItem("analytics:path", e.target.value);
              }}
            >
              {paths.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.goal}{p.version > 1 ? ` (v${p.version})` : ""}
                </option>
              ))}
            </select>
          </div>
          <AnalyticsDashboard pathId={pathId} />
        </>
      )}

      <style>{`
        .analytics-picker {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 16px;
        }

        .analytics-picker label {
          font-size: 13px;
          color: var(--text-secondary);
          font-weight: 600;
        }

        .analytics-picker select {
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          background: var(--bg-primary);
          color: var(--text-primary, inherit);
          font-size: 14px;
          max-width: 420px;
        }

        .analytics-banner {
          padding: 16px 20px;
          border-radius: 8px;
          margin-bottom: 16px;
          font-size: 14px;
        }

        .analytics-banner.empty {
          background: var(--bg-secondary);
          border: 1px dashed var(--border-color);
          color: var(--text-secondary);
          text-align: center;
        }

        .analytics-banner.error {
          background: rgba(244, 67, 54, 0.1);
          border: 1px solid #F44336;
          color: #F44336;
        }
      `}</style>
    </div>
  );
}
