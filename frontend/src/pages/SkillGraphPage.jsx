import { useState, useEffect } from "react";
import { getPathHistory } from "../api/client";
import SkillGraph from "../components/SkillGraph";
import "../components/Layout.css";

export default function SkillGraphPage() {
  const [paths, setPaths] = useState([]);
  const [pathId, setPathId] = useState("");
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    getPathHistory()
      .then((d) => {
        const list = d.paths || [];
        setPaths(list);
        if (list.length) {
          const saved = localStorage.getItem("skills:path");
          const pick = list.find((p) => p.id === saved) ? saved : list[0].id;
          setPathId(pick);
        }
      })
      .catch(() => setError("Failed to load your paths."));
  }, []);

  return (
    <div className="page-container">
      <h1>Skill Graph & Prerequisites</h1>

      {error && <div className="skills-banner error">{error}</div>}

      {!error && paths.length === 0 && (
        <div className="skills-banner empty">
          No learning paths yet. Generate a path first — its skill graph will appear here.
        </div>
      )}

      {paths.length > 0 && (
        <>
          <div className="skills-picker">
            <label htmlFor="skills-path">Path:</label>
            <select
              id="skills-path"
              value={pathId}
              onChange={(e) => {
                setPathId(e.target.value);
                localStorage.setItem("skills:path", e.target.value);
              }}
            >
              {paths.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.goal}{p.version > 1 ? ` (v${p.version})` : ""}
                </option>
              ))}
            </select>
            <button
              className="skills-refresh"
              onClick={() => setReloadKey((k) => k + 1)}
              title="Reload graph"
            >
              ↻ Refresh
            </button>
          </div>
          <SkillGraph key={`${pathId}:${reloadKey}`} pathId={pathId} />
        </>
      )}

      <style>{`
        .skills-picker {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 16px;
        }

        .skills-picker label {
          font-size: 13px;
          color: var(--text-secondary);
          font-weight: 600;
        }

        .skills-picker select {
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          background: var(--bg-primary);
          color: var(--text-primary, inherit);
          font-size: 14px;
          max-width: 380px;
        }

        .skills-refresh {
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          background: var(--bg-primary);
          color: var(--text-primary, inherit);
          cursor: pointer;
          font-size: 13px;
        }

        .skills-refresh:hover {
          border-color: var(--primary-color);
        }

        .skills-banner {
          padding: 16px 20px;
          border-radius: 8px;
          margin-bottom: 16px;
          font-size: 14px;
        }

        .skills-banner.empty {
          background: var(--bg-secondary);
          border: 1px dashed var(--border-color);
          color: var(--text-secondary);
          text-align: center;
        }

        .skills-banner.error {
          background: rgba(244, 67, 54, 0.1);
          border: 1px solid #F44336;
          color: #F44336;
        }
      `}</style>
    </div>
  );
}
