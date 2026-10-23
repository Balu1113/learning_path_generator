import { useEffect, useMemo, useState } from "react";
import { X, LoaderCircle, Check } from "lucide-react";
import { listResource } from "../api.js";
import { labelFor } from "../utils.js";

function initialValue(field, record) {
  if (field.type === "boolean") return record ? !!record[field.name] : false;
  if (!record) return "";
  const v = record[field.name];
  if (v === null || v === undefined) return "";
  if (field.type === "datetime" && typeof v === "string") return v.slice(0, 16);
  return String(v);
}

function buildPayload(fields, values, editing) {
  const payload = {};
  const errors = {};
  for (const f of fields) {
    const required = f.write_only ? !editing : f.required;
    const v = values[f.name];
    const empty = v === "" || v === null || v === undefined;
    if (f.type === "boolean") {
      payload[f.name] = !!v;
      continue;
    }
    if (f.write_only) {
      if (empty) {
        if (required) errors[f.name] = "Required";
      } else {
        payload[f.name] = v;
      }
      continue;
    }
    if (f.type === "string" || f.type === "text") {
      if (empty && required) {
        errors[f.name] = "Required";
        continue;
      }
      payload[f.name] = empty ? "" : String(v);
      continue;
    }
    if (empty) {
      if (required) errors[f.name] = "Required";
      else if (f.nullable) payload[f.name] = null;
      continue;
    }
    payload[f.name] = v;
  }
  return { payload, errors };
}

export default function FormModal({ spec, record, onClose, onSubmit }) {
  const editing = record != null;
  const fields = useMemo(() => spec.fields, [spec]);
  const [values, setValues] = useState(() => {
    const out = {};
    for (const f of fields) out[f.name] = initialValue(f, record);
    return out;
  });
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState("");
  const [busy, setBusy] = useState(false);
  const [fkOptions, setFkOptions] = useState({});

  const fkResources = useMemo(
    () => [...new Set(fields.filter((f) => f.type === "fk").map((f) => f.fk))],
    [fields]
  );

  useEffect(() => {
    for (const res of fkResources) {
      listResource(res, { pageSize: 100 })
        .then((d) => setFkOptions((prev) => ({ ...prev, [res]: d.results })))
        .catch(() => {});
    }
  }, [fkResources]);

  const set = (name, value) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => (prev[name] ? { ...prev, [name]: "" } : prev));
  };

  const renderInput = (f) => {
    const err = errors[f.name];
    const common = { id: `field-${f.name}`, className: err ? "invalid" : "" };
    switch (f.type) {
      case "boolean":
        return (
          <input
            {...common}
            type="checkbox"
            checked={!!values[f.name]}
            onChange={(e) => set(f.name, e.target.checked)}
          />
        );
      case "text":
        return (
          <textarea
            {...common}
            rows={8}
            value={values[f.name]}
            onChange={(e) => set(f.name, e.target.value)}
          />
        );
      case "password":
        return (
          <input
            {...common}
            type="password"
            value={values[f.name]}
            placeholder={editing ? "Leave blank to keep current" : ""}
            autoComplete="new-password"
            onChange={(e) => set(f.name, e.target.value)}
          />
        );
      case "fk": {
        const rows = fkOptions[f.fk] || [];
        return (
          <select
            {...common}
            value={values[f.name]}
            onChange={(e) => set(f.name, e.target.value)}
          >
            <option value="">{f.nullable ? "— none —" : "— select —"}</option>
            {rows.map((row) => (
              <option key={row.id} value={row.id}>
                {row.username || row.name || `#${row.id}`}
              </option>
            ))}
          </select>
        );
      }
      case "choice":
        return (
          <select
            {...common}
            value={values[f.name]}
            onChange={(e) => set(f.name, e.target.value)}
          >
            <option value="">{f.required ? "— select —" : "— none —"}</option>
            {(f.choices || []).map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        );
      case "integer":
      case "float":
        return (
          <input
            {...common}
            type="number"
            step={f.type === "float" ? "any" : "1"}
            value={values[f.name]}
            onChange={(e) => set(f.name, e.target.value)}
          />
        );
      case "date":
        return (
          <input
            {...common}
            type="date"
            value={values[f.name]}
            onChange={(e) => set(f.name, e.target.value)}
          />
        );
      case "datetime":
        return (
          <input
            {...common}
            type="datetime-local"
            value={values[f.name]}
            onChange={(e) => set(f.name, e.target.value)}
          />
        );
      default:
        return (
          <input
            {...common}
            type="text"
            value={values[f.name]}
            onChange={(e) => set(f.name, e.target.value)}
          />
        );
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    const { payload, errors: clientErrors } = buildPayload(fields, values, editing);
    if (Object.keys(clientErrors).length) {
      setErrors(clientErrors);
      setBanner("Please fix the highlighted fields.");
      return;
    }
    setBusy(true);
    setBanner("");
    setErrors({});
    try {
      await onSubmit(payload);
      onClose();
    } catch (err) {
      const serverErrors = err.data && err.data.errors;
      if (serverErrors) {
        const mapped = {};
        const all = [];
        for (const [key, msgs] of Object.entries(serverErrors)) {
          const list = Array.isArray(msgs) ? msgs : [msgs];
          if (key === "__all__") all.push(...list);
          else mapped[key] = list[0];
        }
        setErrors(mapped);
        setBanner(all.join(" ") || "Validation failed.");
      } else {
        setBanner(err.message || "Save failed.");
      }
    } finally {
      setBusy(false);
    }
  };

  const title = editing ? `${spec.label} — edit #${record.id}` : `${spec.label} — new`;

  return (
    <div className="overlay" onClick={busy ? undefined : onClose}>
      <form className="modal form-modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button type="button" className="icon-btn" onClick={onClose} title="Close" disabled={busy}>
            <X size={16} />
          </button>
        </div>
        {banner && <div className="banner error">{banner}</div>}
        <div className="form-grid">
          {fields.map((f) => {
            const required = f.write_only ? !editing : f.required;
            const err = errors[f.name];
            const wide = f.type === "text" || f.name === "goal" || f.name === "content";
            return (
              <label key={f.name} className={`field ${wide ? "span-2" : ""} ${err ? "has-error" : ""}`}>
                <span className="field-label">
                  {labelFor(f.name)}
                  {required && <em className="req"> *</em>}
                  {f.write_only && editing && <em className="hint"> (blank keeps current)</em>}
                </span>
                {renderInput(f)}
                {err && <em className="field-error">{err}</em>}
              </label>
            );
          })}
        </div>
        <div className="modal-actions">
          <button type="button" className="btn subtle" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="btn primary" disabled={busy}>
            {busy ? <LoaderCircle size={15} className="spin" /> : <Check size={15} />} Save
          </button>
        </div>
      </form>
    </div>
  );
}
