import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth.jsx";

// Sign-in and sign-up share one page; `mode` picks the fields and the call.
export default function Auth({ mode }) {
  const isLogin = mode === "login";
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    setBusy(true);
    setErr("");
    try {
      if (!isLogin) await api.register(f);
      const { access_token } = await api.login(isLogin ? f.identifier : f.email, f.password);
      await login(access_token);
      navigate((isLogin && location.state?.from) || "/", { replace: true });
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
          {isLogin ? "Track everything you play." : "Create your account."}
        </p>
        {err && <div className="banner error">{err}</div>}
        <form onSubmit={submit}>
          {isLogin ? (
            <div className="field">
              <label>Email or username</label>
              <input className="input" name="identifier" autoFocus required />
            </div>
          ) : (
            <>
              <div className="field">
                <label>Username</label>
                <input className="input" name="username" autoFocus minLength={3} required />
              </div>
              <div className="field">
                <label>Email</label>
                <input className="input" name="email" type="email" required />
              </div>
            </>
          )}
          <div className="field">
            <label>Password</label>
            <input
              className="input"
              name="password"
              type="password"
              minLength={isLogin ? undefined : 8}
              required
            />
            {!isLogin && (
              <span className="muted" style={{ fontSize: 11 }}>
                At least 8 characters.
              </span>
            )}
          </div>
          <button className="btn primary block" disabled={busy}>
            {isLogin ? (busy ? "Signing in…" : "Sign in") : busy ? "Creating…" : "Create account"}
          </button>
        </form>
        {isLogin && (
          <>
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
          </>
        )}
        <p className="muted" style={{ marginTop: 20, fontSize: 12.5, textAlign: "center" }}>
          {isLogin ? (
            <>
              New here? <Link to="/register">Create an account</Link>
            </>
          ) : (
            <>
              Already have an account? <Link to="/login">Sign in</Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
