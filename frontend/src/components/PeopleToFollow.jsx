import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { initials } from "../lib/util.js";

/** Suggested users with a one-click Follow. Calls onFollowed after a follow. */
export default function PeopleToFollow({ onFollowed }) {
  const [people, setPeople] = useState(null);
  const [busy, setBusy] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .suggestedUsers()
      .then(setPeople)
      .catch((e) => setErr(e.message));
  }, []);

  const follow = async (username) => {
    setBusy(username);
    setErr("");
    try {
      await api.follow(username);
      setPeople((prev) => prev.filter((p) => p.username !== username));
      onFollowed?.(username);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <aside className="panel pad people-panel" aria-labelledby="people-heading">
      <div className="section-head" style={{ marginBottom: 12 }}>
        <h3 id="people-heading" style={{ fontSize: 15 }}>
          People to follow
        </h3>
      </div>

      {err && <div className="banner error">{err}</div>}

      {people === null ? (
        <div className="skeleton-cell">
          {[0, 1, 2].map((i) => (
            <div className="sk-line" key={i} style={{ height: 36, marginTop: 10 }} />
          ))}
        </div>
      ) : people.length === 0 ? (
        <p className="muted" style={{ margin: 0, fontSize: 12.5 }}>
          You're following everyone here. Nice.
        </p>
      ) : (
        <ul className="people-list" role="list">
          {people.map((p) => (
            <li key={p.id} className="person-row">
              <Link to={`/u/${p.username}`} className="avatar" aria-hidden="true">
                {initials(p.username)}
              </Link>
              <div style={{ minWidth: 0, flex: 1 }}>
                <Link to={`/u/${p.username}`} className="person-name">
                  {p.username}
                </Link>
                <span className="meta" style={{ marginTop: 1 }}>
                  {p.games_count} {p.games_count === 1 ? "game" : "games"} ·{" "}
                  {p.followers_count} {p.followers_count === 1 ? "follower" : "followers"}
                </span>
              </div>
              <button
                className="btn sm primary"
                onClick={() => follow(p.username)}
                disabled={busy === p.username}
                aria-label={`Follow ${p.username}`}
              >
                <i className="ph ph-plus" aria-hidden="true" />
                {busy === p.username ? "…" : "Follow"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
