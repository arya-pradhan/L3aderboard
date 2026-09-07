import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import CoverArt from "../components/CoverArt.jsx";
import GameModal from "../components/GameModal.jsx";
import GameRow from "../components/GameRow.jsx";
import { gameMeta } from "../lib/util.js";

const SUGGESTIONS = ["Hollow Knight", "Elden Ring", "Balatro", "Outer Wilds", "Celeste"];

export default function Discover() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const [term, setTerm] = useState(q);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [libraryIds, setLibraryIds] = useState(new Set());
  const [recs, setRecs] = useState([]);
  const [rows, setRows] = useState([]);
  const [rowsLoading, setRowsLoading] = useState(true);
  const [modalGame, setModalGame] = useState(null);

  // On mount: library membership, personalized picks, and discovery rows.
  useEffect(() => {
    api
      .myLibrary()
      .then((r) => setLibraryIds(new Set(r.map((x) => x.game.rawg_id).filter(Boolean))))
      .catch(() => {});
    api
      .recommendations()
      .then(setRecs)
      .catch(() => {});
    api
      .discoverHome()
      .then(setRows)
      .catch(() => {})
      .finally(() => setRowsLoading(false));
  }, []);

  useEffect(() => setTerm(q), [q]);

  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    let alive = true;
    setLoading(true);
    setErr("");
    api
      .searchGames(q, 24)
      .then((r) => alive && setResults(r))
      .catch((e) => alive && setErr(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [q]);

  const submit = (e) => {
    e.preventDefault();
    setParams(term.trim() ? { q: term.trim() } : {});
  };

  const onAdded = (entry) => {
    setLibraryIds((prev) => new Set(prev).add(entry.game.rawg_id));
    setRecs((prev) => prev.filter((g) => g.rawg_id !== entry.game.rawg_id));
    setModalGame(null);
    // Adding (especially with a rating) changes the taste profile, so refresh.
    api
      .recommendations()
      .then(setRecs)
      .catch(() => {});
  };

  const renderCard = (g) => {
    const inLib = libraryIds.has(g.rawg_id);
    return (
      <div className="game-cell" key={g.rawg_id}>
        <button
          onClick={() => !inLib && setModalGame(g)}
          className="cover-btn"
          style={{ cursor: inLib ? "default" : "pointer" }}
          title={inLib ? "Already in your library" : "Add game"}
        >
          <CoverArt game={g} />
        </button>
        <span className="title">{g.title}</span>
        <span className="meta">{gameMeta(g)}</span>
        {inLib ? (
          <span className="chip-accent" style={{ marginTop: 6, display: "inline-flex" }}>
            In library
          </span>
        ) : (
          <button className="btn sm" style={{ marginTop: 8 }} onClick={() => setModalGame(g)}>
            <i className="ph ph-plus" /> Add
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="page">
      {/* hero */}
      <div
        className="panel"
        style={{
          position: "relative",
          overflow: "hidden",
          padding: "40px 36px",
          marginBottom: 30,
          background:
            "radial-gradient(90% 120% at 85% 10%, rgba(196,73,0,.28), transparent 60%), linear-gradient(140deg,#183a37,#04151f 72%)",
        }}
      >
        <span className="kicker">Discover</span>
        <h1 style={{ margin: "12px 0 10px", font: "600 40px/1.05 var(--font)" }}>
          Find your next game.
        </h1>
        <p className="muted" style={{ maxWidth: 460, margin: 0, fontSize: 14, lineHeight: 1.6 }}>
          Search {`≈`}870,000 titles from RAWG, add them to your library, and track what
          you play, rate and abandon.
        </p>
        <form onSubmit={submit} style={{ display: "flex", gap: 10, marginTop: 22, maxWidth: 520 }}>
          <div className="nav-search" style={{ flex: 1, height: 42, width: "auto" }}>
            <i className="ph ph-magnifying-glass" style={{ fontSize: 16, color: "var(--ink-50)" }} />
            <input
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Search games…"
              autoFocus
            />
          </div>
          <button className="btn primary" style={{ height: 42 }}>
            Search
          </button>
        </form>
        {!q && (
          <div className="row" style={{ gap: 6, marginTop: 14, flexWrap: "wrap" }}>
            <span className="muted" style={{ fontSize: 12 }}>
              Try:
            </span>
            {SUGGESTIONS.map((s) => (
              <button key={s} className="pill" onClick={() => setParams({ q: s })}>
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {err && <div className="banner error">{err}</div>}
      {loading && (
        <div className="center">
          <div className="spinner" />
        </div>
      )}

      {/* search results */}
      {!loading && q && results.length === 0 && !err && (
        <div className="empty">No games found for “{q}”.</div>
      )}
      {q && results.length > 0 && (
        <>
          <div className="section-head">
            <h3>Results</h3>
            <span className="sub">{results.length} games</span>
          </div>
          <div className="game-grid">{results.map(renderCard)}</div>
        </>
      )}

      {/* default view: For You + discovery rows */}
      {!q && (
        <>
          {recs.length > 0 ? (
            <GameRow
              title="For you"
              subtitle="based on games you've rated highly"
              games={recs}
              libraryIds={libraryIds}
              onPick={setModalGame}
            />
          ) : (
            <div className="banner info" style={{ marginBottom: 30 }}>
              Rate a few games in your library and personalized picks will appear here.
            </div>
          )}

          {rowsLoading && rows.length === 0 && (
            <div className="center">
              <div className="spinner" />
            </div>
          )}

          {rows.map((row) => (
            <GameRow
              key={row.key}
              title={row.title}
              subtitle={row.subtitle}
              games={row.games}
              libraryIds={libraryIds}
              onPick={setModalGame}
            />
          ))}
        </>
      )}

      {modalGame && (
        <GameModal game={modalGame} onClose={() => setModalGame(null)} onSaved={onAdded} />
      )}
    </div>
  );
}
