import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSharedPath } from "../api/client";
import { Eye, Loader2, Lock } from "lucide-react";
import PathView from "../components/PathView";

function formatDate(raw) {
  const n = Number(raw);
  if (Number.isFinite(n) && n > 0) return new Date(n * 1000).toLocaleDateString();
  const s = String(raw || "");
  return s.length >= 10 ? s.slice(0, 10) : "";
}

export default function SharePage() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    setData(null);
    getSharedPath(slug)
      .then((d) => {
        if (!alive) return;
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => alive && setError("Failed to load the shared roadmap."))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [slug]);

  if (loading) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <Loader2 className="spin" size={32} />
          <p>Loading shared roadmap…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="page-header">
          <Lock size={28} />
          <div>
            <h2>Link unavailable</h2>
            <p className="subtitle">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Eye size={28} />
        <div>
          <h2>{data.goal || "Shared roadmap"}</h2>
          <p className="subtitle">
            Shared learning path — read-only view
            {data.created_at ? ` · created ${formatDate(data.created_at)}` : ""}
          </p>
        </div>
      </div>

      <div className="share-banner">
        <Lock size={14} />
        <span>This version is pinned by its owner. Progress, tests and chat stay private.</span>
      </div>

      <PathView
        readOnly
        format={data.format}
        content={data.content}
        hoursPerDay={data.metadata?.hours_per_day}
      />
    </div>
  );
}
