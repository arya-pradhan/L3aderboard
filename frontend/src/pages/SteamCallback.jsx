import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

// Steam OpenID sends the browser here with #access_token=… in the URL fragment.
export default function SteamCallback() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [err, setErr] = useState("");
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const token = hash.get("access_token");
    if (!token) {
      setErr("No token was returned from Steam.");
      return;
    }
    login(token)
      .then(() => navigate("/", { replace: true }))
      .catch((e) => setErr(e.message));
  }, [login, navigate]);

  return (
    <div className="center">
      {err ? (
        <div style={{ textAlign: "center" }}>
          <div className="banner error">{err}</div>
          <Link to="/login">Back to sign in</Link>
        </div>
      ) : (
        <div className="spinner" />
      )}
    </div>
  );
}
