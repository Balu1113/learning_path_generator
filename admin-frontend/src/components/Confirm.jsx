export default function Confirm({ title, body, confirmLabel = "Delete", onConfirm, onCancel, busy }) {
  return (
    <div className="overlay" onClick={onCancel}>
      <div className="modal confirm" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        {body && <p className="muted">{body}</p>}
        <div className="modal-actions">
          <button className="btn subtle" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="btn danger" onClick={onConfirm} disabled={busy}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
