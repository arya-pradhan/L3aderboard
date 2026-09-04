import { STATUSES, statusLabel } from "../lib/util.js";

export default function StatusFilter({ counts, value, onChange }) {
  return (
    <div className="pills">
      <button className={`pill ${!value ? "active" : ""}`} onClick={() => onChange(null)}>
        All {counts.total}
      </button>
      {STATUSES.map((s) => (
        <button
          key={s}
          className={`pill ${value === s ? "active" : ""}`}
          onClick={() => onChange(s)}
        >
          {statusLabel(s)} {counts.byStatus[s] || 0}
        </button>
      ))}
    </div>
  );
}
