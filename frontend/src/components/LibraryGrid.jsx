import CoverArt from "./CoverArt.jsx";
import { fmtHours } from "../lib/util.js";

export default function LibraryGrid({ entries, editable, onEdit }) {
  if (!entries.length) {
    return <div className="empty">No games here yet.</div>;
  }
  return (
    <div className="game-grid">
      {entries.map((e) => (
        <div className="game-cell" key={e.id}>
          <button
            onClick={() => editable && onEdit(e)}
            className="cover-btn"
            style={{ cursor: editable ? "pointer" : "default" }}
            title={editable ? "Edit entry" : e.game.title}
          >
            <CoverArt game={e.game} status={e.status} score={e.rating ?? undefined} />
          </button>
          <span className="title">{e.game.title}</span>
          <div className="row" style={{ gap: 6, marginTop: 4 }}>
            <span className={`status status-${e.status}`}>{e.status}</span>
            <span className="meta" style={{ marginTop: 0 }}>
              {fmtHours(e.hours_played)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
