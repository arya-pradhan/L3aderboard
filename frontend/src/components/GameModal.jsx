import { useState } from "react";
import { api } from "../api/client.js";
import { STATUSES, statusLabel, gameMeta } from "../lib/util.js";
import CoverArt from "./CoverArt.jsx";

// Add a RAWG game to the library, or edit/remove an existing entry.
export default function GameModal({ game, entry, onClose, onSaved, onDeleted }) {
  const editing = !!entry;
  const g = editing ? entry.game : game;

  const [status, setStatus] = useState(entry?.status || "playing");
  const [rating, setRating] = useState(entry?.rating ?? "");
  const [review, setReview] = useState(entry?.review_text ?? "");
  const [hours, setHours] = useState(entry?.hours_played ?? 0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      const payload = {
        status,
        rating: rating === "" ? null : Number(rating),
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
        <div className="row" style={{ alignItems: "flex-start", gap: 14, marginBottom: 16 }}>
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

        {err && <div className="banner error">{err}</div>}

        <div className="field">
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

        <div className="row" style={{ gap: 12, alignItems: "flex-end" }}>
          <div className="field" style={{ flex: 1, marginBottom: 14 }}>
            <label>Rating</label>
            <select className="input" value={rating} onChange={(e) => setRating(e.target.value)}>
              <option value="">Not rated</option>
              {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={n}>
                  {n} / 10
                </option>
              ))}
            </select>
          </div>
          {editing && (
            <div className="field" style={{ flex: 1, marginBottom: 14 }}>
              <label>Hours played</label>
              <input
                className="input"
                type="number"
                min="0"
                step="0.1"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
              />
            </div>
          )}
        </div>

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
            <button className="btn ghost" style={{ color: "var(--ink-50)" }} onClick={remove} disabled={busy}>
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
