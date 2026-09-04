import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth.jsx";
import { computeStats, fmtDate, initials } from "../lib/util.js";
import StatBand from "../components/StatBand.jsx";
import StatusFilter from "../components/StatusFilter.jsx";
import LibraryGrid from "../components/LibraryGrid.jsx";
import GameModal from "../components/GameModal.jsx";

export default function Profile() {
  const { user, refresh } = useAuth();
  const params = useParams();
  const username = params.username || user.username;

  const [profile, setProfile] = useState(null);
  const [entries, setEntries] = useState(null);
  const [err, setErr] = useState("");
  const [filter, setFilter] = useState(null);
  const [editing, setEditing] = useState(null);
  const [followBusy, setFollowBusy] = useState(false);
  const [importBusy, setImportBusy] = useState(false);
  const [importMsg, setImportMsg] = useState("");

  const load = useCallback(() => {
    setErr("");
    setProfile(null);
    setEntries(null);
    Promise.all([api.profile(username), api.userLibrary(username)])
      .then(([p, lib]) => {
        setProfile(p);
        setEntries(lib);
      })
      .catch((e) => setErr(e.message));
  }, [username]);

  useEffect(() => {
    load();
    setFilter(null);
    setImportMsg("");
  }, [load]);

  const stats = useMemo(() => computeStats(entries || []), [entries]);
  const shown = useMemo(
    () => (filter ? (entries || []).filter((e) => e.status === filter) : entries || []),
    [entries, filter]
  );

  const toggleFollow = async () => {
    setFollowBusy(true);
    try {
      if (profile.is_following) {
        await api.unfollow(username);
        setProfile((p) => ({
          ...p,
          is_following: false,
          followers_count: p.followers_count - 1,
        }));
      } else {
        await api.follow(username);
        setProfile((p) => ({
          ...p,
          is_following: true,
          followers_count: p.followers_count + 1,
        }));
      }
    } catch (e) {
      setErr(e.message);
    } finally {
      setFollowBusy(false);
    }
  };

  const runImport = async () => {
    setImportBusy(true);
    setImportMsg("");
    try {
      const s = await api.steamImport();
      setImportMsg(`Imported ${s.created} new, refreshed ${s.updated} (${s.total_owned} owned).`);
      await refresh();
      load();
    } catch (e) {
      setImportMsg(e.message);
    } finally {
      setImportBusy(false);
    }
  };

  const onSaved = (updated) =>
    setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
  const onDeleted = (id) => setEntries((prev) => prev.filter((e) => e.id !== id));

  if (err) {
    return (
      <div className="page">
        <div className="banner error">{err}</div>
      </div>
    );
  }
  if (!profile || entries === null) {
    return (
      <div className="center">
        <div className="spinner" />
      </div>
    );
  }

  const self = profile.is_self;

  return (
    <div className="page">
      {/* header */}
      <div
        style={{
          margin: "-30px -44px 0",
          padding: "34px 44px 0",
          background: "linear-gradient(180deg, rgba(24,58,55,.5), transparent 88%)",
        }}
      >
        <div className="row" style={{ gap: 20, alignItems: "flex-start" }}>
          <div className="avatar lg">{initials(profile.username)}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="row" style={{ gap: 10 }}>
              <h1 style={{ font: "600 30px/1 var(--font)" }}>{profile.username}</h1>
              {self && user.steam_id && <span className="chip-accent">Steam linked</span>}
            </div>
            <div
              className="row"
              style={{ gap: 16, marginTop: 12, fontSize: 12.5, color: "var(--ink-50)" }}
            >
              <span>
                <b style={{ color: "var(--wheat)" }}>{profile.following_count}</b> following
              </span>
              <span>
                <b style={{ color: "var(--wheat)" }}>{profile.followers_count}</b> followers
              </span>
              <span>joined {fmtDate(profile.created_at)}</span>
            </div>
          </div>
          <div className="row" style={{ gap: 9 }}>
            {self ? (
              user.steam_id ? (
                <button className="btn primary" onClick={runImport} disabled={importBusy}>
                  <i className="ph ph-arrows-clockwise" />
                  {importBusy ? "Importing…" : "Sync Steam"}
                </button>
              ) : (
                <a className="btn primary" href={api.steamLoginUrl()}>
                  <i className="ph ph-steam-logo" /> Link Steam
                </a>
              )
            ) : (
              <button
                className={`btn ${profile.is_following ? "" : "primary"}`}
                onClick={toggleFollow}
                disabled={followBusy}
              >
                <i className={`ph ph-${profile.is_following ? "check" : "plus"}`} />
                {profile.is_following ? "Following" : "Follow"}
              </button>
            )}
          </div>
        </div>

        <StatBand stats={stats} />
      </div>

      {importMsg && (
        <div className="banner info" style={{ marginTop: 20 }}>
          {importMsg}
        </div>
      )}

      {/* library */}
      <div style={{ marginTop: 30 }}>
        <div className="section-head" style={{ alignItems: "center" }}>
          <h3>{self ? "My library" : "Library"}</h3>
          <span className="sub">{stats.total} games</span>
          <div className="spacer" />
          <StatusFilter counts={stats} value={filter} onChange={setFilter} />
        </div>
        <LibraryGrid entries={shown} editable={self} onEdit={setEditing} />
      </div>

      {editing && (
        <GameModal
          entry={editing}
          onClose={() => setEditing(null)}
          onSaved={(u) => {
            onSaved(u);
            setEditing(null);
          }}
          onDeleted={(id) => {
            onDeleted(id);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
