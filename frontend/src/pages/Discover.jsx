import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import GameCase from "../components/GameCase.jsx";
import GameModal from "../components/GameModal.jsx";
import GameRow from "../components/GameRow.jsx";

const SUGGESTIONS = ["Hollow Knight", "Elden Ring", "Balatro", "Outer Wilds", "Celeste"];

export default function Discover() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const [term, setTerm] = useState(q);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  // rawg_id -> library entry, so owned games open in edit mode.
  const [library, setLibrary] = useState(new Map());
  const [recs, setRecs] = useState([]);
  const [rows, setRows] = useState([]);
  const [rowsLoading, setRowsLoading] = useState(true);
  const [modalGame, setModalGame] = useState(null);

  // On mount: library membership, personalized picks, and discovery rows.
  useEffect(() => {
    api
      .myLibrary()
      .then((r) => setLibrary(new Map(r.filter((x) => x.game.rawg_id).map((x) => [x.game.rawg_id, x]))))
      .catch(() => {});
    api
      .recommendations(24)
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

  const onSaved = (entry) => {
    setLibrary((prev) => new Map(prev).set(entry.game.rawg_id, entry));
    setRecs((prev) => prev.filter((g) => g.rawg_id !== entry.game.rawg_id));
    setModalGame(null);
    // Adding (especially with a rating) changes the taste profile, so refresh.
    api
      .recommendations(24)
      .then(setRecs)
      .catch(() => {});
  };

  const onDeleted = () => {
    setLibrary((prev) => {
      const next = new Map(prev);
      next.delete(modalGame.rawg_id);
      return next;
    });
    setModalGame(null);
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
          background: "linear-gradient(115deg, #183a37 0%, #04151f 62%)",
        }}
      >
        {/* the mockup's diagonal hatch — the brand's editorial texture */}
        <div className="hero-hatch" aria-hidden="true" />
        <h1 style={{ margin: "0 0 12px", font: "800 clamp(44px, 9vw, 64px)/0.9 var(--display)" }}>
          Find your next game.
        </h1>
        <p className="muted" style={{ maxWidth: 460, margin: 0, fontSize: 14, lineHeight: 1.6 }}>
          Search {`≈`}870,000 titles from RAWG, add them to your library, and track what
          you play, rate and abandon.
        </p>
        <form onSubmit={submit} style={{ display: "flex", gap: 10, marginTop: 22, maxWidth: 520 }}>
          <div className="nav-search" style={{ flex: 1, height: 44, width: "auto" }}>
            <i className="ph ph-magnifying-glass" style={{ fontSize: 16, color: "var(--ink-50)" }} />
            <input
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Search games…"
              autoFocus
            />
          </div>
          <button className="btn primary" style={{ height: 44 }}>
            Search
          </button>
        </form>
        {!q && (
          <div className="row" style={{ gap: 6, marginTop: 14, flexWrap: "wrap" }}>
            <span className="muted" style={{ fontSize: 12 }}>
              Try:
            </span>
            {SUGGESTIONS.map((s) => (
              <button key={s} className="pill plain" onClick={() => setParams({ q: s })}>
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
          <div className="game-grid" role="list">
            {results.map((g) => (
              <GameCase key={g.rawg_id} game={g} inLibrary={library.has(g.rawg_id)} onPick={setModalGame} />
            ))}
          </div>
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
              libraryIds={library}
              onPick={setModalGame}
            />
          ) : (
            <div className="banner info" style={{ marginBottom: 30 }}>
              Rate a few games in your library and personalized picks will appear here.
            </div>
          )}

          {rowsLoading && rows.length === 0 && (
            <>
              <GameRow title="Popular this year" loading />
              <GameRow title="New & upcoming" loading />
            </>
          )}

          {rows.map((row) => (
            <GameRow
              key={row.key}
              title={row.title}
              subtitle={row.subtitle}
              games={row.games}
              libraryIds={library}
              onPick={setModalGame}
            />
          ))}
        </>
      )}

      {modalGame && (
        <GameModal
          game={modalGame}
          entry={library.get(modalGame.rawg_id)}
          onClose={() => setModalGame(null)}
          onSaved={onSaved}
          onDeleted={onDeleted}
        />
      )}
    </div>
  );
}
