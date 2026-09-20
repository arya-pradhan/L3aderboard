import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import CoverArt from "../components/CoverArt.jsx";
import PeopleToFollow from "../components/PeopleToFollow.jsx";
import { fmtHours, gameMeta, initials, statusLabel, timeAgo } from "../lib/util.js";

export default function Feed() {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api
      .feed()
      .then(setItems)
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="page">
      <div className="feed-layout">
        <section aria-labelledby="feed-heading">
          <div className="section-head">
            <h3 id="feed-heading">Activity feed</h3>
            <span className="sub">recent updates from people you follow</span>
          </div>

          {err && <div className="banner error">{err}</div>}

          {items === null && !err && (
            <div className="skeleton-cell">
              {[0, 1, 2, 3].map((i) => (
                <div className="sk-line" key={i} style={{ height: 76, marginTop: 12 }} />
              ))}
            </div>
          )}

          {items && items.length === 0 && (
            <div className="empty" role="status">
              <i
                className="ph ph-users-three"
                style={{ fontSize: 28, display: "block", marginBottom: 8, color: "var(--ink-40)" }}
                aria-hidden="true"
              />
              Your feed is quiet. Follow a few people and their activity will show up here.
            </div>
          )}

          {items && items.length > 0 && (
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
                        aria-hidden="true"
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
        </section>

        <PeopleToFollow onFollowed={load} />
      </div>
    </div>
  );
}
