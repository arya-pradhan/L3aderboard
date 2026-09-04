import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const { access_token } = await api.login(identifier, password);
      await login(access_token);
      navigate(location.state?.from || "/", { replace: true });
    } catch (e2) {
      setErr(e2.message);
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="brand">
          L<b>3</b>ADERBOARD
        </div>
        <p className="muted" style={{ margin: "6px 0 22px", fontSize: 13 }}>
          Track everything you play.
        </p>
        {err && <div className="banner error">{err}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Email or username</label>
            <input
              className="input"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              autoFocus
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className="btn primary block" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="row" style={{ margin: "16px 0" }}>
          <div className="hr" style={{ margin: 0, flex: 1 }} />
          <span className="muted" style={{ fontSize: 11 }}>
            or
          </span>
          <div className="hr" style={{ margin: 0, flex: 1 }} />
        </div>
        <a className="btn block" href={api.steamLoginUrl()}>
          <i className="ph ph-steam-logo" style={{ fontSize: 16 }} /> Continue with Steam
        </a>
        <p className="muted" style={{ marginTop: 20, fontSize: 12.5, textAlign: "center" }}>
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
