import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { STATUSES, coverSrc, gameMeta, statusLabel } from "../lib/util.js";

const RATINGS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
// RAWG's community rating buckets, best first.
const SHARE_ORDER = ["exceptional", "recommended", "meh", "skip"];

function metacriticTier(score) {
  if (score >= 75) return "good";
  if (score >= 50) return "mixed";
  return "bad";
}

// What RAWG players think: average score, the vote split, Metacritic, playtime.
// Every field is optional: an older API (or a RAWG gap) must not crash the page.
function RawgScore({ detail }) {
  const ratings = detail.ratings || [];
  const shares = SHARE_ORDER.map((t) => ratings.find((r) => r.title === t)).filter(Boolean);
  if (!detail.rating && !detail.metacritic && !detail.playtime) return null;
  return (
    <div className="gm-scores">
      {detail.rating && (
        <div className="gm-rawg">
          <div className="gm-rawg-head">
            <span className="gm-rawg-num">{detail.rating.toFixed(1)}</span>
            <span className="gm-rawg-of">
              out of 5 from {(detail.ratings_count || 0).toLocaleString()} RAWG ratings
            </span>
          </div>
          {shares.length > 0 && (
            <>
              <div className="gm-split" aria-hidden="true">
                {shares.map((r) => (
                  <span key={r.title} className={`seg-${r.title}`} style={{ flexGrow: r.percent }} />
                ))}
              </div>
              <ul className="gm-split-legend">
                {shares.map((r) => (
                  <li key={r.title}>
                    <span className={`swatch seg-${r.title}`} aria-hidden="true" />
                    {statusLabel(r.title)} {Math.round(r.percent)}%
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
      <div className="gm-facts">
        {detail.metacritic != null && (
          <div className="gm-fact">
            <span className={`mc mc-${metacriticTier(detail.metacritic)}`}>{detail.metacritic}</span>
            Metacritic
          </div>
        )}
        {detail.playtime && (
          <div className="gm-fact">
            <span className="gm-fact-num">{detail.playtime}h</span>
            Average playtime
          </div>
        )}
      </div>
    </div>
  );
}

// A game's popup: RAWG screenshots and ratings, plus adding it to your
// library or editing your existing entry.
export default function GameModal({ game, entry, onClose, onSaved, onDeleted }) {
  const editing = !!entry;
  const g = editing ? entry.game : game;

  const [status, setStatus] = useState(entry?.status || "playing");
  const [rating, setRating] = useState(entry?.rating ?? null);
  const [review, setReview] = useState(entry?.review_text ?? "");
  const [hours, setHours] = useState(entry?.hours_played ?? 0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Search/browse results carry no description, screenshots or ratings.
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(!!g.rawg_id);
  const [shot, setShot] = useState(0);
  const [descExpanded, setDescExpanded] = useState(false);
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!g.rawg_id) return;
    let alive = true;
    api
      .gameDetail(g.rawg_id)
      .then((d) => alive && setDetail(d))
      .catch(() => {})
      .finally(() => alive && setDetailLoading(false));
    return () => {
      alive = false;
    };
  }, [g.rawg_id]);

  // Escape closes; focus moves into the dialog; the page behind stops scrolling.
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && closeRef.current();
    document.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, []);

  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      const payload = { status, rating: rating ?? null, review_text: review.trim() || null };
      const result = editing
        ? await api.updateEntry(entry.id, { ...payload, hours_played: Number(hours) || 0 })
        : await api.addToLibrary({ rawg_id: g.rawg_id, ...payload });
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

  const description = detail?.description || g.description;
  const shots = detail?.screenshots?.length ? detail.screenshots : g.cover_url ? [g.cover_url] : [];
  const platforms = (detail?.platforms || g.platforms || []).slice(0, 5);

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div
        className="modal game-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="gm-title"
        tabIndex={-1}
        ref={dialogRef}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <button className="btn icon gm-close" onClick={onClose} aria-label="Close">
          <i className="ph ph-x" aria-hidden="true" />
        </button>

        <div className="gm-media">
          <div className={`gm-screen ${detailLoading && !shots.length ? "loading" : ""}`}>
            {shots[shot] && <img src={coverSrc(shots[shot], 1280)} alt={`${g.title} screenshot ${shot + 1}`} />}
          </div>
          {shots.length > 1 && (
            <div className="gm-thumbs" role="group" aria-label="Screenshots">
              {shots.map((url, i) => (
                <button
                  key={url}
                  className={`gm-thumb ${i === shot ? "active" : ""}`}
                  onClick={() => setShot(i)}
                  aria-label={`Show screenshot ${i + 1}`}
                  aria-pressed={i === shot}
                >
                  <img src={coverSrc(url, 200)} alt="" loading="lazy" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="gm-body">
          <div className="gm-info">
            <h2 id="gm-title">{g.title}</h2>
            <p className="gm-meta">{gameMeta(g) || "Release date unknown"}</p>
            {platforms.length > 0 && (
              <ul className="gm-platforms" aria-label="Platforms">
                {platforms.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            )}

            {detail && <RawgScore detail={detail} />}

            {detailLoading && !description && <p className="desc muted">Loading details…</p>}
            {description && (
              <>
                <p className={`desc ${descExpanded ? "" : "clamped"}`}>{description}</p>
                {description.length > 260 && (
                  <button className="desc-toggle" onClick={() => setDescExpanded((v) => !v)}>
                    {descExpanded ? "Show less" : "Show more"}
                  </button>
                )}
              </>
            )}
          </div>

          <div className="gm-log">
            <h3>{editing ? "Your log" : "Add to your library"}</h3>
            {err && <div className="banner error">{err}</div>}

            <div className="field">
              <label id="gm-status">Status</label>
              <div className="pills" role="group" aria-labelledby="gm-status">
                {STATUSES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`pill led-${s} ${status === s ? "active" : ""}`}
                    aria-pressed={status === s}
                    onClick={() => setStatus(s)}
                  >
                    {statusLabel(s)}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label id="gm-rating">Your rating {rating ? `${rating}/10` : ""}</label>
              <div className="rating-grid" role="group" aria-labelledby="gm-rating">
                {RATINGS.map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={`rating-btn ${rating === n ? "active" : ""}`}
                    aria-pressed={rating === n}
                    onClick={() => setRating(rating === n ? null : n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            {editing && (
              <div className="field">
                <label htmlFor="gm-hours">Hours played</label>
                <input
                  id="gm-hours"
                  className="input"
                  type="number"
                  min="0"
                  step="0.1"
                  value={hours}
                  onChange={(e) => setHours(e.target.value)}
                  style={{ maxWidth: 140 }}
                />
              </div>
            )}

            <div className="field">
              <label htmlFor="gm-review">Review</label>
              <textarea
                id="gm-review"
                className="input"
                placeholder="Optional. What did you think?"
                value={review}
                onChange={(e) => setReview(e.target.value)}
              />
            </div>

            <div className="row gm-actions">
              {editing && (
                <button className="btn ghost" onClick={remove} disabled={busy}>
                  <i className="ph ph-trash" aria-hidden="true" /> Remove
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
      </div>
    </div>
  );
}
