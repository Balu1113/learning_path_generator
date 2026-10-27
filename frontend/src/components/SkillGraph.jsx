import React, { useState, useEffect, useCallback } from 'react';
import {
  getSkillGraph,
  getPhaseBlockers,
  getCriticalPath,
  getSkillPrerequisites,
  getSkillUnlocks,
  extractSkills,
} from '../api/client';

const NODE_W = 150;
const NODE_H = 44;
const COL_GAP = 210;
const ROW_GAP = 64;
const PAD = 24;

const STATE_COLORS = {
  unassessed: { fill: '#eceff1', stroke: '#90a4ae', text: '#546e7a' },
  developing: { fill: '#fff3e0', stroke: '#FF9800', text: '#e65100' },
  validated: { fill: '#e8f5e9', stroke: '#4CAF50', text: '#2e7d32' },
};

function layoutGraph(nodes) {
  const byPhase = new Map();
  nodes.forEach((n) => {
    const p = n.phase ?? 0;
    if (!byPhase.has(p)) byPhase.set(p, []);
    byPhase.get(p).push(n);
  });
  const phases = [...byPhase.keys()].sort((a, b) => a - b);
  const maxRows = Math.max(...phases.map((p) => byPhase.get(p).length), 1);
  const height = maxRows * ROW_GAP + PAD * 2;
  const positions = {};
  phases.forEach((phase, col) => {
    const list = byPhase.get(phase);
    const colHeight = list.length * ROW_GAP;
    const offset = (height - colHeight) / 2;
    list.forEach((n, row) => {
      positions[n.id] = {
        x: PAD + col * COL_GAP,
        y: Math.round(offset + row * ROW_GAP),
      };
    });
  });
  const width = PAD * 2 + Math.max(0, phases.length - 1) * COL_GAP + NODE_W;
  return { positions, width, height, phases };
}

function truncate(text, n) {
  if (!text) return '';
  return text.length > n ? `${text.slice(0, n - 1)}…` : text;
}

const SkillGraph = ({ pathId }) => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [blockers, setBlockers] = useState([]);
  const [critical, setCritical] = useState([]);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadGraph = useCallback(async () => {
    if (!pathId) return;
    setLoading(true);
    setError('');
    try {
      const [graphRes, blockersRes, criticalRes] = await Promise.all([
        getSkillGraph(pathId),
        getPhaseBlockers(pathId),
        getCriticalPath(pathId),
      ]);

      if (graphRes.error) {
        setError(graphRes.error);
        setNodes([]);
        setEdges([]);
        return;
      }
      setNodes(graphRes.nodes || []);
      setEdges(graphRes.edges || []);
      setBlockers(blockersRes.warnings || []);
      setCritical(criticalRes.critical_skills || []);
      setSelected(null);
      setDetail(null);
    } catch (err) {
      console.error('Failed to load skill graph:', err);
      setError('Failed to load the skill graph. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [pathId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return undefined;
    }
    let alive = true;
    setDetailLoading(true);
    Promise.all([
      getSkillPrerequisites(selected.id),
      getSkillUnlocks(selected.id),
    ])
      .then(([prereqs, unlocks]) => {
        if (!alive) return;
        setDetail({
          prerequisites: prereqs.prerequisites || [],
          unlocks: unlocks.unlocks || [],
        });
      })
      .catch(() => {
        if (alive) setDetail({ prerequisites: [], unlocks: [] });
      })
      .finally(() => {
        if (alive) setDetailLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [selected]);

  const handleExtract = async () => {
    setExtracting(true);
    setError('');
    try {
      const res = await extractSkills(pathId);
      if (res.error) {
        setError(res.error);
      } else {
        await loadGraph();
      }
    } catch (err) {
      console.error('Failed to extract skills:', err);
      setError('Skill extraction failed. Please try again.');
    } finally {
      setExtracting(false);
    }
  };

  if (!pathId) {
    return <div className="skill-graph-loading">Select a path to view its skill graph.</div>;
  }

  if (loading) {
    return <div className="skill-graph-loading">Loading skill graph...</div>;
  }

  if (error && nodes.length === 0) {
    return (
      <div className="skill-graph-loading">
        <p>{error}</p>
        <button className="extract-btn" onClick={loadGraph}>Retry</button>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="skill-extract-cta">
        <h3>No skill graph yet</h3>
        <p>
          Extract the skills and prerequisites from this learning path to see
          the dependency graph, phase warnings, and critical skills.
        </p>
        {error && <p className="extract-error">{error}</p>}
        <button className="extract-btn" onClick={handleExtract} disabled={extracting}>
          {extracting ? 'Extracting skills with AI…' : 'Extract Skills'}
        </button>
      </div>
    );
  }

  const criticalIds = new Set(critical.map((c) => c.skill_id));
  const nodeById = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const { positions, width, height, phases } = layoutGraph(nodes);

  const selectedIds = selected
    ? new Set([
        selected.id,
        ...edges.filter((e) => e.from === selected.id || e.to === selected.id)
          .flatMap((e) => [e.from, e.to]),
      ])
    : null;

  return (
    <div className="skill-graph">
      {error && <div className="skill-warning error">{error}</div>}

      {blockers.length > 0 && (
        <div className="skill-section">
          <h3>⚠️ Phase Warnings ({blockers.length})</h3>
          <ul className="blocker-list">
            {blockers.map((w, idx) => (
              <li key={idx} className="blocker-item">
                <span className="blocker-icon">🔒</span>
                <span>{w.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {critical.length > 0 && (
        <div className="skill-section">
          <h3>🎯 Critical Path ({critical.length} skills)</h3>
          <div className="critical-chips">
            {critical.map((c) => (
              <button
                key={c.skill_id}
                className={`critical-chip ${selected?.id === c.skill_id ? 'active' : ''}`}
                onClick={() => setSelected(nodeById[c.skill_id] || null)}
                title={`${c.prerequisite_count} prerequisites · unlocks ${c.unlocks_count} skills · ${c.phase_title}`}
              >
                <span className="chip-star">★</span> {c.skill}
                <span className="chip-phase">{c.phase_title}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="skill-section">
        <h3>Skill Dependency Graph</h3>
        <div className="graph-scroll">
          <svg
            width={width}
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            className="graph-svg"
            role="img"
            aria-label="Skill dependency graph"
          >
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
                markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#90a4ae" />
              </marker>
              <marker id="arrow-hi" viewBox="0 0 10 10" refX="9" refY="5"
                markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#FF9800" />
              </marker>
            </defs>

            {phases.map((phase, col) => (
              <text
                key={`label-${phase}`}
                x={PAD + col * COL_GAP + NODE_W / 2}
                y={14}
                textAnchor="middle"
                className="phase-label"
              >
                Phase {phase + 1}
              </text>
            ))}

            {edges.map((e, idx) => {
              const from = positions[e.from];
              const to = positions[e.to];
              if (!from || !to) return null;
              const x1 = from.x + NODE_W;
              const y1 = from.y + NODE_H / 2;
              const x2 = to.x;
              const y2 = to.y + NODE_H / 2;
              const dx = Math.max(40, (x2 - x1) * 0.5);
              const highlighted = selectedIds && (selectedIds.has(e.from) && selectedIds.has(e.to));
              return (
                <path
                  key={`e-${e.from}-${e.to}-${idx}`}
                  d={`M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`}
                  fill="none"
                  stroke={highlighted ? '#FF9800' : '#b0bec5'}
                  strokeWidth={highlighted ? 2.5 : 1.5}
                  markerEnd={highlighted ? 'url(#arrow-hi)' : 'url(#arrow)'}
                />
              );
            })}

            {nodes.map((n) => {
              const pos = positions[n.id];
              if (!pos) return null;
              const colors = STATE_COLORS[n.state] || STATE_COLORS.unassessed;
              const isCritical = criticalIds.has(n.id);
              const isSelected = selected?.id === n.id;
              const dimmed = selectedIds && !selectedIds.has(n.id);
              return (
                <g
                  key={n.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  className={`graph-node ${dimmed ? 'dimmed' : ''}`}
                  onClick={() => setSelected(isSelected ? null : n)}
                  style={{ cursor: 'pointer' }}
                >
                  <rect
                    width={NODE_W}
                    height={NODE_H}
                    rx={8}
                    fill={colors.fill}
                    stroke={isSelected ? '#2196F3' : (isCritical ? '#FF9800' : colors.stroke)}
                    strokeWidth={isSelected || isCritical ? 2.5 : 1.5}
                    strokeDasharray={isCritical && !isSelected ? '5 3' : undefined}
                  />
                  <text
                    x={NODE_W / 2}
                    y={NODE_H / 2 - 3}
                    textAnchor="middle"
                    className="node-name"
                    fill={colors.text}
                  >
                    {truncate(n.name, 18)}
                  </text>
                  <text
                    x={NODE_W / 2}
                    y={NODE_H / 2 + 12}
                    textAnchor="middle"
                    className="node-state"
                    fill={colors.text}
                  >
                    {n.state}{n.score != null ? ` · ${n.score}%` : ''}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        <div className="graph-legend">
          {Object.entries(STATE_COLORS).map(([state, colors]) => (
            <span key={state} className="legend-item">
              <span className="legend-swatch" style={{ background: colors.fill, borderColor: colors.stroke }} />
              {state}
            </span>
          ))}
          <span className="legend-item">
            <span className="legend-swatch critical" />
            critical skill
          </span>
        </div>
      </div>

      {selected && (
        <div className="skill-section skill-detail">
          <div className="detail-header">
            <h3>{selected.name}</h3>
            <button className="detail-close" onClick={() => setSelected(null)}>✕</button>
          </div>
          <div className="detail-meta">
            <span className={`state-badge ${selected.state}`}>{selected.state}</span>
            {selected.domain && <span className="meta-chip">{selected.domain}</span>}
            <span className="meta-chip">Phase {(selected.phase ?? 0) + 1}</span>
            {selected.score != null && <span className="meta-chip">score {selected.score}%</span>}
          </div>
          {selected.description && <p className="detail-description">{selected.description}</p>}
          {selected.topics && selected.topics.length > 0 && (
            <p className="detail-topics">
              <strong>Topics:</strong> {selected.topics.join(', ')}
            </p>
          )}

          {detailLoading ? (
            <p className="detail-loading">Loading connections…</p>
          ) : (
            <div className="detail-columns">
              <div className="detail-column">
                <h4>Requires ({detail?.prerequisites?.length || 0})</h4>
                {(detail?.prerequisites || []).length === 0 ? (
                  <p className="detail-empty">No prerequisites — you can start anytime.</p>
                ) : (
                  <ul className="connection-list">
                    {detail.prerequisites.map((p) => (
                      <li key={p.id}>
                        <button
                          className="connection-link"
                          onClick={() => nodeById[p.id] && setSelected(nodeById[p.id])}
                        >
                          {p.name}
                        </button>
                        {!nodeById[p.id] && <span className="connection-note"> (outside this path)</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="detail-column">
                <h4>Unlocks ({detail?.unlocks?.length || 0})</h4>
                {(detail?.unlocks || []).length === 0 ? (
                  <p className="detail-empty">Nothing depends on this skill yet.</p>
                ) : (
                  <ul className="connection-list">
                    {detail.unlocks.map((u) => (
                      <li key={u.id}>
                        <button
                          className="connection-link"
                          onClick={() => nodeById[u.id] && setSelected(nodeById[u.id])}
                        >
                          {u.name}
                        </button>
                        {!nodeById[u.id] && <span className="connection-note"> (outside this path)</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .skill-graph-loading {
          padding: 40px;
          text-align: center;
          color: var(--text-secondary);
        }

        .skill-extract-cta {
          padding: 40px;
          text-align: center;
          background: var(--bg-secondary);
          border: 1px dashed var(--border-color);
          border-radius: 8px;
          color: var(--text-secondary);
        }

        .skill-extract-cta h3 {
          margin-top: 0;
          color: var(--text-primary);
        }

        .extract-btn {
          margin-top: 12px;
          padding: 10px 20px;
          background: linear-gradient(135deg, #4CAF50, #2196F3);
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: bold;
        }

        .extract-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .extract-error {
          color: #F44336;
          font-weight: 600;
        }

        .skill-warning.error {
          padding: 12px 16px;
          background: rgba(244, 67, 54, 0.1);
          border: 1px solid #F44336;
          border-radius: 8px;
          color: #F44336;
          margin-bottom: 16px;
        }

        .skill-section {
          margin-bottom: 24px;
        }

        .skill-section h3 {
          margin: 0 0 12px;
          color: var(--text-primary);
          font-size: 16px;
        }

        .blocker-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .blocker-item {
          display: flex;
          gap: 10px;
          align-items: flex-start;
          padding: 10px 12px;
          background: #fff8e1;
          border: 1px solid #ffe082;
          border-radius: 6px;
          font-size: 13px;
        }

        .critical-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .critical-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 10px;
          background: #fff3e0;
          border: 1px solid #FF9800;
          border-radius: 999px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
          color: #e65100;
        }

        .critical-chip.active {
          background: #FF9800;
          color: white;
        }

        .chip-star {
          color: #FFC107;
        }

        .critical-chip.active .chip-star {
          color: white;
        }

        .chip-phase {
          font-weight: 400;
          font-size: 11px;
          opacity: 0.8;
        }

        .graph-scroll {
          overflow-x: auto;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          padding: 8px;
        }

        .graph-svg {
          display: block;
          min-width: 100%;
        }

        .phase-label {
          font-size: 11px;
          fill: var(--text-secondary, #78909c);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .node-name {
          font-size: 12px;
          font-weight: 700;
        }

        .node-state {
          font-size: 9.5px;
        }

        .graph-node.dimmed {
          opacity: 0.35;
        }

        .graph-legend {
          display: flex;
          flex-wrap: wrap;
          gap: 14px;
          margin-top: 10px;
          font-size: 12px;
          color: var(--text-secondary);
        }

        .legend-item {
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }

        .legend-swatch {
          width: 14px;
          height: 14px;
          border-radius: 4px;
          border: 2px solid #90a4ae;
          display: inline-block;
        }

        .legend-swatch.critical {
          background: #fff3e0;
          border-color: #FF9800;
          border-style: dashed;
        }

        .skill-detail {
          padding: 16px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
        }

        .detail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .detail-close {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 16px;
          color: var(--text-secondary);
        }

        .detail-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 10px 0;
        }

        .state-badge {
          padding: 3px 10px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 700;
          text-transform: capitalize;
        }

        .state-badge.unassessed { background: #eceff1; color: #546e7a; }
        .state-badge.developing { background: #fff3e0; color: #e65100; }
        .state-badge.validated { background: #e8f5e9; color: #2e7d32; }

        .meta-chip {
          padding: 3px 10px;
          border-radius: 999px;
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          font-size: 12px;
          color: var(--text-secondary);
        }

        .detail-description {
          font-size: 14px;
          color: var(--text-secondary);
          margin: 8px 0;
        }

        .detail-topics {
          font-size: 13px;
          margin: 8px 0;
        }

        .detail-loading,
        .detail-empty {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .detail-columns {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin-top: 12px;
        }

        .detail-column h4 {
          margin: 0 0 8px;
          font-size: 13px;
          text-transform: uppercase;
          color: var(--text-secondary);
        }

        .connection-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .connection-link {
          background: none;
          border: none;
          padding: 0;
          color: var(--primary-color, #2196F3);
          cursor: pointer;
          font-size: 14px;
          font-weight: 600;
          text-align: left;
        }

        .connection-link:hover {
          text-decoration: underline;
        }

        .connection-note {
          font-size: 12px;
          color: var(--text-secondary);
        }

        @media (max-width: 768px) {
          .detail-columns {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default SkillGraph;
