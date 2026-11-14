import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import GameCase from "../components/GameCase.jsx";
import GameModal from "../components/GameModal.jsx";
import GameRow from "../components/GameRow.jsx";
import Spotlight from "../components/Spotlight.jsx";

const SUGGESTIONS = ["Hollow Knight", "Elden Ring", "Balatro", "Outer Wilds", "Celeste"];
const SPOTLIGHT_SIZE = 6;
const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

// A genre's shelf, fetched only when it scrolls within reach.
function GenreShelf({ genre, library, onPick }) {
  const ref = useRef(null);
  const [games, setGames] = useState(null);
  useEffect(() => {
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        api.genreShelf(genre.slug).then(setGames).catch(() => setGames([]));
      },
      { rootMargin: "900px 0px" }
    );
    io.observe(ref.current);
    return () => io.disconnect();
  }, [genre.slug]);
  return (
    <div ref={ref} id={`genre-${genre.slug}`} className="genre-anchor" data-slug={genre.slug}>
      {games === null ? (
        <GameRow title={genre.name} loading />
      ) : (
        <GameRow
          title={genre.name}
          subtitle="popular in this genre"
          games={games}
          libraryIds={library}
          onPick={onPick}
        />
      )}
    </div>
  );
}

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
  const [genres, setGenres] = useState([]);
  const [activeGenre, setActiveGenre] = useState(null);
  const [modalGame, setModalGame] = useState(null);
  const jumpingUntil = useRef(0); // in-view tracking pauses while a jump scrolls

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
    api
      .discoverGenres()
      .then(setGenres)
      .catch(() => {}); // older API: the home rows' own genre rows stay instead
  }, []);

  // Light the genre switch for whichever shelf crosses the middle of the screen.
  useEffect(() => {
    if (q || !genres.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (Date.now() < jumpingUntil.current) return;
        for (const e of entries) {
          const slug = e.target.dataset.slug;
          // Above or below the genre shelves, no switch is lit.
          setActiveGenre((cur) => (e.isIntersecting ? slug : cur === slug ? null : cur));
        }
      },
      { rootMargin: "-45% 0px -50% 0px" }
    );
    document.querySelectorAll(".genre-anchor").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [genres, q]);

  // Keep the lit switch visible when the strip is wider than the screen.
  // Scroll only the strip: scrollIntoView would also nudge the page and
  // cancel a jump that's still animating.
  useEffect(() => {
    const strip = document.querySelector(".genre-strip");
    const pill = strip?.querySelector(".pill.active");
    if (!pill) return;
    const { left, right } = pill.getBoundingClientRect();
    const box = strip.getBoundingClientRect();
    if (left >= box.left && right <= box.right) return;
    strip.scrollTo({
      left: pill.offsetLeft - (strip.clientWidth - pill.offsetWidth) / 2,
      behavior: reducedMotion() ? "auto" : "smooth",
    });
  }, [activeGenre]);

  // The clicked genre lights at once; the last shelves can't scroll up to
  // the middle of the screen, so in-view tracking would pick a neighbour.
  const jumpTo = (slug) => {
    setActiveGenre(slug);
    jumpingUntil.current = Date.now() + 1200;
    document
      .getElementById(`genre-${slug}`)
      ?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
  };

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

  const popular = rows.find((r) => r.key === "popular");
  const spotlight = (popular?.games || []).filter((g) => g.cover_url).slice(0, SPOTLIGHT_SIZE);
  // With per-genre shelves available, the home rows' two genre rows are redundant.
  const homeRows = genres.length ? rows.filter((r) => !r.key.startsWith("genre:")) : rows;

  return (
    <div className="page">
      <form className="discover-search" onSubmit={submit} role="search">
        <div className="nav-search">
          <i className="ph ph-magnifying-glass" aria-hidden="true" />
          <input
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="Search 870,000 games"
            aria-label="Search games"
          />
        </div>
        <button className="btn primary">Search</button>
        {!q && (
          <div className="discover-try">
            <span className="muted">Try</span>
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" className="pill plain" onClick={() => setParams({ q: s })}>
                {s}
              </button>
            ))}
          </div>
        )}
      </form>

      {err && <div className="banner error">{err}</div>}
      {loading && (
        <div className="center">
          <div className="spinner" />
        </div>
      )}

      {!loading && q && results.length === 0 && !err && (
        <div className="empty">No games match “{q}”. Check the spelling or try a shorter title.</div>
      )}
      {q && results.length > 0 && (
        <>
          <div className="section-head">
            <h3>Results for “{q}”</h3>
            <span className="sub">{results.length} games</span>
          </div>
          <div className="game-grid" role="list">
            {results.map((g) => (
              <GameCase key={g.rawg_id} game={g} inLibrary={library.has(g.rawg_id)} onPick={setModalGame} />
            ))}
          </div>
        </>
      )}

      {!q && (
        <>
          {spotlight.length > 0 ? (
            <Spotlight title={popular.title} games={spotlight} library={library} onOpen={setModalGame} />
          ) : (
            rowsLoading && <div className="spot loading" aria-busy="true" aria-label="Loading featured games" />
          )}

          {genres.length > 0 && (
            <nav className="genre-strip" aria-label="Jump to a genre">
              <span className="genre-strip-label">Genres</span>
              {genres.map((g) => (
                <button
                  key={g.slug}
                  type="button"
                  className={`pill ${activeGenre === g.slug ? "active" : ""}`}
                  aria-current={activeGenre === g.slug || undefined}
                  onClick={() => jumpTo(g.slug)}
                >
                  {g.name}
                </button>
              ))}
            </nav>
          )}

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

          {homeRows.map((row) => (
            <GameRow
              key={row.key}
              title={row.title}
              subtitle={row.subtitle}
              games={row.games}
              libraryIds={library}
              onPick={setModalGame}
            />
          ))}

          {genres.map((g) => (
            <GenreShelf key={g.slug} genre={g} library={library} onPick={setModalGame} />
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
