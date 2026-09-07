import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { STATUSES, statusLabel, gameMeta } from "../lib/util.js";
import CoverArt from "./CoverArt.jsx";

const RATINGS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

// Add a RAWG game to the library, or edit/remove an existing entry.
export default function GameModal({ game, entry, onClose, onSaved, onDeleted }) {
  const editing = !!entry;
  const g = editing ? entry.game : game;

  const [status, setStatus] = useState(entry?.status || "playing");
  const [rating, setRating] = useState(entry?.rating ?? null);
  const [review, setReview] = useState(entry?.review_text ?? "");
  const [hours, setHours] = useState(entry?.hours_played ?? 0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // RAWG only returns descriptions from its detail endpoint, so a game coming
  // from search/browse results needs one fetched on open.
  const [description, setDescription] = useState(g.description || null);
  const [descLoading, setDescLoading] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);

  useEffect(() => {
    if (description || !g.rawg_id) return;
    let alive = true;
    setDescLoading(true);
    api
      .gameDetail(g.rawg_id)
      .then((full) => alive && setDescription(full.description || null))
      .catch(() => {})
      .finally(() => alive && setDescLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [g.rawg_id]);

  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      const payload = {
        status,
        rating: rating ?? null,
        review_text: review.trim() || null,
      };
      let result;
      if (editing) {
        payload.hours_played = Number(hours) || 0;
        result = await api.updateEntry(entry.id, payload);
      } else {
        result = await api.addToLibrary({ rawg_id: g.rawg_id, ...payload });
      }
      onSaved(result);
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setErr("");
    try {
      await api.deleteEntry(entry.id);
      onDeleted(entry.id);
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="row" style={{ alignItems: "flex-start", gap: 14, marginBottom: 8 }}>
          <CoverArt game={g} style={{ width: 70, flex: "none" }} />
          <div style={{ minWidth: 0 }}>
            <h2>{g.title}</h2>
            <span className="muted" style={{ fontSize: 12 }}>
              {gameMeta(g) || "—"}
            </span>
          </div>
          <div className="spacer" />
          <button className="btn icon" style={{ borderColor: "transparent" }} onClick={onClose}>
            <i className="ph ph-x" />
          </button>
        </div>

        {descLoading && !description && (
          <p className="desc muted" style={{ fontStyle: "italic" }}>
            Loading description…
          </p>
        )}
        {description && (
          <>
            <p className={`desc ${descExpanded ? "" : "clamped"}`}>{description}</p>
            {description.length > 260 && (
              <button
                className="desc-toggle"
                onClick={() => setDescExpanded((v) => !v)}
              >
                {descExpanded ? "Show less" : "Show more"}
              </button>
            )}
          </>
        )}

        {err && (
          <div className="banner error" style={{ marginTop: 14 }}>
            {err}
          </div>
        )}

        <div className="field" style={{ marginTop: 16 }}>
          <label>Status</label>
          <div className="pills">
            {STATUSES.map((s) => (
              <button
                key={s}
                type="button"
                className={`pill ${status === s ? "active" : ""}`}
                onClick={() => setStatus(s)}
              >
                {statusLabel(s)}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Rating {rating ? `— ${rating}/10` : ""}</label>
          <div className="rating-grid">
            {RATINGS.map((n) => (
              <button
                key={n}
                type="button"
                className={`rating-btn ${rating === n ? "active" : ""}`}
                onClick={() => setRating(n)}
              >
                {n}
              </button>
            ))}
            {rating != null && (
              <button type="button" className="rating-clear" onClick={() => setRating(null)}>
                Clear
              </button>
            )}
          </div>
        </div>

        {editing && (
          <div className="field">
            <label>Hours played</label>
            <input
              className="input"
              type="number"
              min="0"
              step="0.1"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              style={{ maxWidth: 160 }}
            />
          </div>
        )}

        <div className="field">
          <label>Review</label>
          <textarea
            className="input"
            placeholder="Optional — what did you think?"
            value={review}
            onChange={(e) => setReview(e.target.value)}
          />
        </div>

        <div className="row" style={{ marginTop: 8 }}>
          {editing && (
            <button
              className="btn ghost"
              style={{ color: "var(--ink-50)" }}
              onClick={remove}
              disabled={busy}
            >
              <i className="ph ph-trash" /> Remove
            </button>
          )}
          <div className="spacer" />
          <button className="btn" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className="btn primary" onClick={save} disabled={busy}>
            {editing ? "Save changes" : "Add to library"}
          </button>
        </div>
      </div>
    </div>
  );
}
