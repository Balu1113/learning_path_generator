import { useCallback, useEffect, useState } from "react";
import {
  createGroup, getGroup, getGroups, getPathHistory, joinGroup, leaveGroup, setGroupPath,
} from "../api/client";
import { useAuth } from "../auth";
import {
  ArrowLeft, Check, Copy, Crown, KeyRound, Loader2, LogIn, UserMinus, UserPlus, Users,
} from "lucide-react";

export default function Groups() {
  const { user } = useAuth();
  const [groups, setGroups] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [copied, setCopied] = useState(false);
  const [paths, setPaths] = useState([]);
  const [attachId, setAttachId] = useState("");

  const loadList = useCallback(() => {
    getGroups()
      .then((d) => {
        if (d.error) setError(d.error);
        else setGroups(d.groups || []);
      })
      .catch(() => setError("Failed to load groups."));
  }, []);

  useEffect(() => {
    if (!user) {
      setGroups(null);
      return;
    }
    loadList();
  }, [user, loadList]);

  const loadDetail = useCallback((id) => {
    setError("");
    setNote("");
    getGroup(id)
      .then((d) => {
        if (d.error) setError(d.error);
        else setDetail(d);
      })
      .catch(() => setError("Failed to load the group."));
  }, []);

  useEffect(() => {
    if (!detail?.is_owner) return;
    getPathHistory()
      .then((d) => {
        if (!d.error) setPaths(d.paths || []);
      })
      .catch(() => {});
  }, [detail?.is_owner]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const d = await createGroup(name.trim());
      if (d.error) setError(d.error);
      else {
        setName("");
        setNote(`Group "${d.group.name}" created — invite code ${d.group.code}`);
        loadList();
      }
    } catch {
      setError("Creating the group failed.");
    }
    setBusy(false);
  };

  const handleJoin = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const d = await joinGroup(code.trim());
      if (d.error) setError(d.error);
      else {
        setCode("");
        loadDetail(d.group.id);
        loadList();
      }
    } catch {
      setError("Joining failed.");
    }
    setBusy(false);
  };

  const handleLeave = async (id) => {
    if (!window.confirm("Leave this group?")) return;
    setBusy(true);
    setError("");
    try {
      const d = await leaveGroup(id);
      if (d.error) setError(d.error);
      else {
        setDetail(null);
        loadList();
      }
    } catch {
      setError("Leaving the group failed.");
    }
    setBusy(false);
  };

  const handleSetPath = async (pathId) => {
    setBusy(true);
    setError("");
    try {
      const d = await setGroupPath(detail.id, pathId);
      if (d.error) setError(d.error);
      else loadDetail(detail.id);
    } catch {
      setError("Changing the group roadmap failed.");
    }
    setBusy(false);
  };

  const copyCode = async (value) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copy failed — select the code and copy it manually.");
    }
  };

  if (!user) {
    return (
      <div className="page-container">
        <div className="page-header">
          <Users size={28} />
          <div>
            <h2>Study Groups</h2>
            <p className="subtitle">Learn together with a shared roadmap.</p>
          </div>
        </div>
        <div className="empty-state">
          <LogIn size={48} />
          <p>Log in to create or join study groups.</p>
        </div>
      </div>
    );
  }

  if (detail) {
    return (
      <div className="page-container">
        <div className="page-header">
          <Users size={28} />
          <div>
            <h2>{detail.name}</h2>
            <p className="subtitle">
              Owned by {detail.owner_name} · {detail.member_count} member{detail.member_count === 1 ? "" : "s"}
            </p>
          </div>
        </div>

        {error && <div className="error-box">{error}</div>}
        {note && <p className="saved-note">{note}</p>}

        <div className="group-detail-bar">
          <button className="btn-secondary" onClick={() => setDetail(null)}>
            <ArrowLeft size={14} /> All groups
          </button>
          <button
            className="btn-secondary group-code-chip"
            onClick={() => copyCode(detail.code)}
            title="Copy invite code"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />} Code: {detail.code}
          </button>
          <button className="btn-secondary" onClick={() => handleLeave(detail.id)} disabled={busy}>
            <UserMinus size={14} /> Leave group
          </button>
        </div>

        <div className="help-section">
          <h3><KeyRound size={16} /> Shared roadmap</h3>
          {detail.path_goal ? (
            <p><strong>{detail.path_goal}</strong> — member progress below.</p>
          ) : (
            <p className="subtitle">No roadmap attached yet.</p>
          )}
          {detail.is_owner && (
            <div className="group-attach">
              <select value={attachId} onChange={(e) => setAttachId(e.target.value)}>
                <option value="">Choose one of your saved paths…</option>
                {paths.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.goal}{p.version > 1 ? ` (v${p.version})` : ""}
                  </option>
                ))}
              </select>
              <button className="btn-secondary" disabled={busy || !attachId}
                      onClick={() => { handleSetPath(attachId); setAttachId(""); }}>
                Attach
              </button>
              {detail.path_id && (
                <button className="btn-secondary" disabled={busy}
                        onClick={() => handleSetPath("")}>
                  Clear
                </button>
              )}
            </div>
          )}
        </div>

        <div className="help-section">
          <h3><Users size={16} /> Members</h3>
          <div className="group-members">
            {detail.members.map((m) => (
              <div key={m.id} className="group-member-row">
                <div className="group-member-name">
                  {m.is_owner && <Crown size={14} />}
                  <strong>{m.username}</strong>
                </div>
                <div className="group-member-progress">
                  {m.progress.percent !== null ? (
                    <>
                      <div className="progress-bar-wrap">
                        <div className="progress-bar" style={{ width: `${m.progress.percent}%` }} />
                        <span className="progress-label">{m.progress.done}/{m.progress.total} · {m.progress.percent}%</span>
                      </div>
                    </>
                  ) : (
                    <span className="subtitle">No shared roadmap</span>
                  )}
                </div>
                <span className="group-member-meta">
                  {m.last_active ? `active ${m.last_active}` : "not active yet"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Users size={28} />
        <div>
          <h2>Study Groups</h2>
          <p className="subtitle">Invite friends with a code and track progress on one roadmap.</p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {note && <p className="saved-note">{note}</p>}

      <div className="group-forms">
        <form className="help-section" onSubmit={handleCreate}>
          <h3><UserPlus size={16} /> Create a group</h3>
          <div className="group-attach">
            <input
              type="text"
              placeholder="Group name, e.g. Python Sprint"
              value={name}
              maxLength={80}
              onChange={(e) => setName(e.target.value)}
            />
            <button className="btn-primary" disabled={busy || !name.trim()}>
              {busy ? <Loader2 className="spin" size={16} /> : <UserPlus size={16} />} Create
            </button>
          </div>
        </form>

        <form className="help-section" onSubmit={handleJoin}>
          <h3><KeyRound size={16} /> Join with a code</h3>
          <div className="group-attach">
            <input
              type="text"
              placeholder="Invite code, e.g. K7XQ2M"
              value={code}
              maxLength={12}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
            />
            <button className="btn-primary" disabled={busy || !code.trim()}>
              {busy ? <Loader2 className="spin" size={16} /> : <KeyRound size={16} />} Join
            </button>
          </div>
        </form>
      </div>

      {groups === null ? (
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Loading your groups…</p>
        </div>
      ) : groups.length === 0 ? (
        <div className="empty-state">
          <Users size={48} />
          <p>You are not in any study groups yet. Create one and share the invite code.</p>
        </div>
      ) : (
        <div className="gallery-grid">
          {groups.map((g) => (
            <div key={g.id} className="gallery-card group-card">
              <div className="gallery-card-top">
                <span className="gallery-format structured">{g.member_count} member{g.member_count === 1 ? "" : "s"}</span>
                <button
                  className="btn-icon"
                  title="Copy invite code"
                  onClick={() => copyCode(g.code)}
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
              <h3>{g.name}</h3>
              <p className="gallery-goal">Owner: {g.owner_name} · code {g.code}</p>
              <p className="gallery-summary">{g.path_goal || "No roadmap attached yet"}</p>
              <div className="group-card-actions">
                <button className="btn-primary" onClick={() => loadDetail(g.id)}>
                  Open
                </button>
                <button className="btn-secondary" onClick={() => handleLeave(g.id)} disabled={busy}>
                  <UserMinus size={14} /> Leave
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
