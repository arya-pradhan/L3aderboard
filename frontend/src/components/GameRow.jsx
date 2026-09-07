import { useEffect, useRef, useState } from "react";
import CoverArt from "./CoverArt.jsx";
import { gameMeta } from "../lib/util.js";

/** Horizontal, scrollable row of games (mockup 1a style). */
export default function GameRow({ title, subtitle, games, libraryIds, onPick }) {
  const trackRef = useRef(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const sync = () => {
    const el = trackRef.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  };

  useEffect(() => {
    sync();
  }, [games]);

  const scrollBy = (dir) => {
    const el = trackRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.round(el.clientWidth * 0.85), behavior: "smooth" });
  };

  if (!games || games.length === 0) return null;

  return (
    <section className="game-row">
      <div className="section-head">
        <h3>{title}</h3>
        {subtitle && <span className="sub">{subtitle}</span>}
      </div>

      <button
        className="row-arrow left"
        onClick={() => scrollBy(-1)}
        disabled={atStart}
        aria-label="Scroll left"
      >
        <i className="ph ph-caret-left" />
      </button>
      <button
        className="row-arrow right"
        onClick={() => scrollBy(1)}
        disabled={atEnd}
        aria-label="Scroll right"
      >
        <i className="ph ph-caret-right" />
      </button>

      <div className="row-track" ref={trackRef} onScroll={sync}>
        {games.map((g) => {
          const inLib = libraryIds?.has(g.rawg_id);
          return (
            <div className="game-cell" key={g.rawg_id}>
              <button
                className="cover-btn"
                style={{ cursor: inLib ? "default" : "pointer" }}
                onClick={() => !inLib && onPick(g)}
                title={inLib ? "Already in your library" : g.title}
              >
                <CoverArt game={g} />
              </button>
              <span className="title">{g.title}</span>
              <span className="meta">{gameMeta(g)}</span>
              {inLib ? (
                <span
                  className="chip-accent"
                  style={{ marginTop: 6, display: "inline-flex" }}
                >
                  In library
                </span>
              ) : (
                <button
                  className="btn sm"
                  style={{ marginTop: 8 }}
                  onClick={() => onPick(g)}
                >
                  <i className="ph ph-plus" /> Add
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
