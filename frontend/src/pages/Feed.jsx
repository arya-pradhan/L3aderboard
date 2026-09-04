import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import CoverArt from "../components/CoverArt.jsx";
import { fmtHours, gameMeta, initials, statusLabel, timeAgo } from "../lib/util.js";

export default function Feed() {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .feed()
      .then(setItems)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) {
    return (
      <div className="page">
        <div className="banner error">{err}</div>
      </div>
    );
  }
  if (items === null) {
    return (
      <div className="center">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="section-head">
        <h3>Activity feed</h3>
        <span className="sub">recent updates from people you follow</span>
      </div>

      {items.length === 0 ? (
        <div className="empty">
          Your feed is quiet. Follow people (visit a profile at <code>/u/username</code>) to
          see what they're playing.
        </div>
      ) : (
        <div>
          {items.map((i) => (
            <div className="feed-item" key={i.entry_id}>
              <CoverArt game={i.game} status={i.status} style={{ width: 46, flex: "none" }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                  <Link
                    to={`/u/${i.user.username}`}
                    className="avatar"
                    style={{ width: 22, height: 22, fontSize: 9 }}
                  >
                    {initials(i.user.username)}
                  </Link>
                  <Link
                    to={`/u/${i.user.username}`}
                    style={{ color: "var(--wheat)", fontWeight: 600, fontSize: 13 }}
                  >
                    {i.user.username}
                  </Link>
                  <span className={`status status-${i.status}`}>{statusLabel(i.status)}</span>
                  {i.rating != null && (
                    <span className="muted" style={{ fontSize: 12 }}>
                      rated {i.rating}/10
                    </span>
                  )}
                  <div className="spacer" />
                  <span className="muted" style={{ fontSize: 11 }}>
                    {timeAgo(i.updated_at)}
                  </span>
                </div>
                <div style={{ marginTop: 6, fontSize: 13.5, color: "var(--wheat)" }}>
                  {i.game.title}
                </div>
                <div className="meta" style={{ marginTop: 2 }}>
                  {gameMeta(i.game, fmtHours(i.hours_played))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
