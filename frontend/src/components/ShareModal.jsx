import { useEffect, useState } from "react";
import { createShare, getShare, revokeShare } from "../api/client";
import { Check, Copy, ExternalLink, Globe, Loader2, Trash2, X } from "lucide-react";

export default function ShareModal({ pathId, onClose }) {
  const [share, setShare] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    setShare(null);
    setCopied(false);
    getShare(pathId)
      .then((d) => {
        if (!alive) return;
        if (d.error) setError(d.error);
        else if (d.slug) setShare(d);
      })
      .catch(() => alive && setError("Could not load share settings."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [pathId]);

  const link = share ? `${window.location.origin}${share.url}` : "";

  const create = async () => {
    setBusy(true);
    setError("");
    try {
      const d = await createShare(pathId);
      if (d.error) setError(d.error);
      else setShare(d);
    } catch {
      setError("Creating the link failed.");
    }
    setBusy(false);
  };

  const revoke = async () => {
    setBusy(true);
    setError("");
    try {
      const d = await revokeShare(pathId);
      if (d.error) setError(d.error);
      else {
        setShare(null);
        setCopied(false);
      }
    } catch {
      setError("Revoking the link failed.");
    }
    setBusy(false);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copy failed — select the link and copy it manually.");
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Share roadmap</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="modal-body">
          {error && <div className="error-box">{error}</div>}

          {loading ? (
            <p className="subtitle"><Loader2 className="spin" size={14} /> Checking link status…</p>
          ) : share ? (
            <>
              <p>
                Anyone with this link can view <strong>this version</strong> of the roadmap —
                no sign-in needed. It also appears in the public <strong>Gallery</strong>.
                Revoking cuts access immediately.
              </p>
              <div className="share-url-row">
                <input type="text" readOnly value={link} onFocus={(e) => e.target.select()} />
                <button className="btn-primary" onClick={copy}>
                  {copied ? <><Check size={16} /> Copied</> : <><Copy size={16} /> Copy</>}
                </button>
              </div>
              <div className="modal-actions">
                <a
                  className="btn-secondary"
                  href={share.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink size={16} /> Open preview
                </a>
                <button className="btn-secondary" onClick={revoke} disabled={busy}>
                  {busy ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />} Revoke link
                </button>
              </div>
            </>
          ) : (
            <>
              <p>
                Create a public read-only link to this roadmap. Visitors get a page at
                <code> /p/&lt;slug&gt;</code>, and it becomes browsable in the public
                Gallery; progress, chat and exports stay private to you.
              </p>
              <div className="modal-actions">
                <button className="btn-primary" onClick={create} disabled={busy}>
                  {busy ? <Loader2 className="spin" size={16} /> : <Globe size={16} />} Create public link
                </button>
                <button className="btn-secondary" onClick={onClose}>Cancel</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
