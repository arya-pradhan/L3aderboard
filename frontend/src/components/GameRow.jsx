import { useEffect, useRef, useState } from "react";
import CoverArt from "./CoverArt.jsx";
import { gameMeta } from "../lib/util.js";

const SKELETON_COUNT = 7;

/** Horizontal, scrollable row of games (mockup 1a style). */
export default function GameRow({ title, subtitle, games, libraryIds, onPick, loading }) {
  const trackRef = useRef(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const sync = () => {
    const el = trackRef.current;
    if (!el) return;
    // Tolerant thresholds: sub-pixel/snap rounding shouldn't flip the edge fades.
    setAtStart(el.scrollLeft <= 8);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 8);
  };

  useEffect(() => {
    sync();
  }, [games]);

  const scrollBy = (dir) => {
    const el = trackRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.round(el.clientWidth * 0.85), behavior: "smooth" });
  };

  if (loading) {
    return (
      <section className="game-row" aria-busy="true" aria-label={`Loading ${title}`}>
        <div className="section-head">
          <h3>{title}</h3>
          {subtitle && <span className="sub">{subtitle}</span>}
        </div>
        <div className="row-track">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <div className="skeleton-cell" key={i}>
              <div className="sk-cover" />
              <div className="sk-line" />
              <div className="sk-line short" />
            </div>
          ))}
        </div>
      </section>
    );
  }

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
        aria-label={`Scroll ${title} left`}
      >
        <i className="ph ph-caret-left" aria-hidden="true" />
      </button>
      <button
        className="row-arrow right"
        onClick={() => scrollBy(1)}
        disabled={atEnd}
        aria-label={`Scroll ${title} right`}
      >
        <i className="ph ph-caret-right" aria-hidden="true" />
      </button>

      <div
        className={`row-track ${atStart ? "" : "fade-l"} ${atEnd ? "" : "fade-r"}`}
        ref={trackRef}
        onScroll={sync}
        role="list"
      >
        {games.map((g) => {
          const inLib = libraryIds?.has(g.rawg_id);
          return (
            <div className="game-cell" key={g.rawg_id} role="listitem">
              <button
                className={`cover-btn ${inLib ? "static" : ""}`}
                style={{ cursor: inLib ? "default" : "pointer" }}
                onClick={() => !inLib && onPick(g)}
                title={inLib ? `${g.title} — already in your library` : `Add ${g.title}`}
                aria-label={inLib ? `${g.title}, already in your library` : `Add ${g.title}`}
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
                <button className="btn sm" style={{ marginTop: 8 }} onClick={() => onPick(g)}>
                  <i className="ph ph-plus" aria-hidden="true" /> Add
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
