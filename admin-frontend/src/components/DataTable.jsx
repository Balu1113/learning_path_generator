import { Pencil, Trash } from "lucide-react";
import { labelFor } from "../utils.js";

function cellText(row, col) {
  const key = `${col}_label` in row ? `${col}_label` : col;
  const value = row[key];
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function DataTable({ columns, rows, sortable = [], sort, onSort, onRowClick, onDelete }) {
  if (!rows.length) {
    return <div className="empty">No records found.</div>;
  }
  return (
    <table className="table">
      <thead>
        <tr>
          {columns.map((col) => {
            const isSortable = sortable.includes(col);
            return (
              <th
                key={col}
                className={isSortable ? "sortable" : ""}
                onClick={isSortable ? () => onSort(col) : undefined}
              >
                {labelFor(col)}
                {sort === col ? " ▲" : sort === `-${col}` ? " ▼" : ""}
              </th>
            );
          })}
          <th className="actions-col" />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} onClick={() => onRowClick && onRowClick(row)} className={onRowClick ? "clickable" : ""}>
            {columns.map((col) => {
              const text = cellText(row, col);
              return (
                <td key={col} title={text}>
                  {text}
                </td>
              );
            })}
            <td className="actions-col" onClick={(e) => e.stopPropagation()}>
              {onRowClick && (
                <button className="icon-btn" title="Edit" onClick={() => onRowClick(row)}>
                  <Pencil size={14} />
                </button>
              )}
              {onDelete && (
                <button className="icon-btn danger" title="Delete" onClick={() => onDelete(row)}>
                  <Trash size={14} />
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
