import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Plus, Search, ChevronLeft, ChevronRight, LoaderCircle } from "lucide-react";
import {
  createResource,
  deleteResource,
  fetchResource,
  listResource,
  updateResource,
} from "../api.js";
import { useMeta } from "../context.jsx";
import DataTable from "../components/DataTable.jsx";
import FormModal from "../components/FormModal.jsx";
import Confirm from "../components/Confirm.jsx";

const PAGE_SIZE = 20;

export default function Resource() {
  const { resource } = useParams();
  return <ResourceView key={resource} resource={resource} />;
}

function ResourceView({ resource }) {
  const { resources, error: metaError } = useMeta();
  const spec = resources ? resources[resource] : null;

  const [rows, setRows] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(undefined);
  const [confirming, setConfirming] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    listResource(resource, { page, pageSize: PAGE_SIZE, search: query, sort })
      .then((d) => {
        setRows(d.results);
        setCount(d.count);
      })
      .catch((e) => {
        setError(
          e.status === 403
            ? "Admin access required — sign in again."
            : e.message || "Failed to load records"
        );
      })
      .finally(() => setLoading(false));
  }, [resource, page, query, sort]);

  useEffect(() => {
    if (resources) {
      if (spec) load();
      else setLoading(false);
    }
  }, [resources, spec, load]);

  const toggleSort = (col) => {
    if (sort === col) setSort(`-${col}`);
    else if (sort === `-${col}`) setSort("");
    else setSort(col);
    setPage(1);
  };

  const openRow = async (row) => {
    try {
      const d = await fetchResource(resource, row.id);
      setEditing(d.result);
    } catch (e) {
      setError(e.message || "Failed to load record");
    }
  };

  const submitForm = async (payload) => {
    if (editing === null) await createResource(resource, payload);
    else await updateResource(resource, editing.id, payload);
    load();
  };

  const doDelete = async () => {
    setBusy(true);
    try {
      await deleteResource(resource, confirming.id);
      setConfirming(null);
      if (rows.length === 1 && page > 1) setPage(page - 1);
      load();
    } catch (e) {
      setError(e.message || "Delete failed");
      setConfirming(null);
    } finally {
      setBusy(false);
    }
  };

  if (metaError) return <div className="banner error">{metaError}</div>;
  if (!resources) {
    return (
      <p className="muted">
        <LoaderCircle size={14} className="spin" /> Loading metadata…
      </p>
    );
  }
  if (!spec) {
    return (
      <div className="banner error">
        Unknown resource “{resource}”. <Link to="/">Back to dashboard</Link>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <div>
      <header className="page-head">
        <h2>{spec.label}</h2>
        <div className="head-actions">
          <div className="search-box">
            <Search size={14} />
            <input
              value={search}
              placeholder={
                spec.search.length ? `Search ${spec.search.join(", ")}…` : "Search…"
              }
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button className="btn primary" onClick={() => setEditing(null)}>
            <Plus size={15} /> New {spec.label.replace(/s$/, "").toLowerCase()}
          </button>
        </div>
      </header>

      {error && <div className="banner error">{error}</div>}

      <div className="table-wrap">
        {loading ? (
          <div className="empty">
            <LoaderCircle size={16} className="spin" /> Loading…
          </div>
        ) : (
          <DataTable
            columns={spec.display}
            rows={rows}
            sortable={spec.sortable}
            sort={sort}
            onSort={toggleSort}
            onRowClick={openRow}
            onDelete={setConfirming}
          />
        )}
      </div>

      <div className="pager">
        <button className="btn subtle" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>
          <ChevronLeft size={14} /> Prev
        </button>
        <span>
          Page {page} of {totalPages} · {count} records
        </span>
        <button
          className="btn subtle"
          disabled={page >= totalPages || loading}
          onClick={() => setPage(page + 1)}
        >
          Next <ChevronRight size={14} />
        </button>
      </div>

      {editing !== undefined && (
        <FormModal
          spec={spec}
          record={editing}
          onClose={() => setEditing(undefined)}
          onSubmit={submitForm}
        />
      )}

      {confirming && (
        <Confirm
          title={`Delete ${spec.label.toLowerCase()} #${confirming.id}?`}
          body={
            resource === "users"
              ? "Deleting a user cascades to their progress, flashcards, activity, tests and badges."
              : "This cannot be undone."
          }
          onConfirm={doDelete}
          onCancel={() => setConfirming(null)}
          busy={busy}
        />
      )}
    </div>
  );
}
