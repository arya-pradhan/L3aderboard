import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { initials } from "../lib/util.js";

export default function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  const submit = (e) => {
    e.preventDefault();
    const term = q.trim();
    if (term) navigate(`/?q=${encodeURIComponent(term)}`);
  };

  return (
    <header className="nav">
      <NavLink to="/" className="brand" style={{ display: "inline-flex" }}>
        L<b>3</b>ADERBOARD
      </NavLink>
      <nav className="nav-links">
        <NavLink to="/" end>
          Discover
        </NavLink>
        <NavLink to="/library">Library</NavLink>
        <NavLink to="/feed">Feed</NavLink>
      </nav>
      <div className="spacer" />
      <form className="nav-search" onSubmit={submit}>
        <i className="ph ph-magnifying-glass" style={{ fontSize: 14, color: "var(--ink-50)" }} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search games…"
          aria-label="Search games"
        />
      </form>
      <div className="row" style={{ gap: 8 }}>
        <NavLink to={`/u/${user.username}`} className="avatar" title={user.username}>
          {initials(user.username)}
        </NavLink>
        <button
          className="btn icon"
          style={{ height: 32, width: 32, borderColor: "transparent", color: "var(--ink-50)" }}
          onClick={() => {
            logout();
            navigate("/login");
          }}
          title="Log out"
        >
          <i className="ph ph-sign-out" style={{ fontSize: 15 }} />
        </button>
      </div>
    </header>
  );
}
