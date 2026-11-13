import { useEffect, useLayoutEffect, useRef } from "react";
import GameCase from "./GameCase.jsx";

const SKELETON_COUNT = 8;
// Fewer games than this fit on screen anyway, so looping would just repeat them.
const MIN_TO_LOOP = 8;

/**
 * A shelf of CDs that scrolls sideways and loops: the games are rendered three
 * times, and whenever scrolling settles in an outer copy we jump (instantly,
 * invisibly) by one copy's width back into the middle one.
 */
export default function GameRow({ title, subtitle, games, libraryIds, onPick, loading }) {
  const trackRef = useRef(null);
  const animRef = useRef(0);
  const loops = !loading && games?.length >= MIN_TO_LOOP;

  // Width of one copy = distance between the first item of copy 0 and copy 1.
  const copyWidth = () => {
    const el = trackRef.current;
    const n = games.length;
    return el.children[n].offsetLeft - el.children[0].offsetLeft;
  };

  const jump = (delta) => {
    const el = trackRef.current;
    el.style.scrollBehavior = "auto";
    el.scrollLeft += delta;
    el.style.scrollBehavior = "";
  };

  // Start in the middle copy before first paint.
  useLayoutEffect(() => {
    if (loops) jump(copyWidth() - trackRef.current.scrollLeft);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loops, games]);

  // Outside the middle copy? Jump one copy width back into it (looks identical).
  const recenter = () => {
    const el = trackRef.current;
    const w = copyWidth();
    if (el.scrollLeft < w * 0.5) jump(w);
    else if (el.scrollLeft > w * 1.5) jump(-w);
  };

  // Swipes and trackpad flings: re-center once scrolling settles.
  useEffect(() => {
    const el = trackRef.current;
    if (!loops || !el) return;
    let timer;
    const onScroll = () => {
      clearTimeout(timer);
      timer = setTimeout(() => el.style.scrollSnapType !== "none" && recenter(), 160);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(animRef.current);
      el.removeEventListener("scroll", onScroll);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loops, games]);

  // Arrows move by whole cases. Animated by hand: Chromium silently drops a
  // smooth scrollTo issued right after the previous one ends. Re-centering
  // first means rapid clicks can't run past the clones.
  const scrollByPage = (dir) => {
    const el = trackRef.current;
    cancelAnimationFrame(animRef.current);
    if (loops) recenter();
    const step = el.children[1].offsetLeft - el.children[0].offsetLeft;
    const perPage = Math.max(1, Math.floor((el.clientWidth * 0.85) / step));
    const from = el.scrollLeft;
    const to = Math.round(from / step) * step + dir * perPage * step;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const t0 = performance.now();
    el.style.scrollSnapType = "none"; // snapping would fight each frame
    const frame = (now) => {
      const t = reduce ? 1 : Math.min(1, (now - t0) / 380);
      el.scrollLeft = from + (to - from) * (1 - (1 - t) ** 3); // ease-out cubic
      if (t < 1) animRef.current = requestAnimationFrame(frame);
      else el.style.scrollSnapType = "";
    };
    animRef.current = requestAnimationFrame(frame);
  };

  const head = (
    <div className="section-head">
      <h3>{title}</h3>
      {subtitle && <span className="sub">{subtitle}</span>}
    </div>
  );

  if (loading) {
    return (
      <section className="game-row" aria-busy="true" aria-label={`Loading ${title}`}>
        {head}
        <div className="row-track">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <div className="case-cell skeleton" key={i}>
              <div className="sk-case" />
              <div className="sk-line" />
              <div className="sk-line short" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!games || games.length === 0) return null;

  const copies = loops ? [0, 1, 2] : [1];

  return (
    <section className="game-row" aria-label={title}>
      {head}
      {loops && (
        <>
          <button
            className="row-arrow left"
            onClick={() => scrollByPage(-1)}
            aria-label={`Scroll ${title} back`}
          >
            <i className="ph ph-caret-left" aria-hidden="true" />
          </button>
          <button
            className="row-arrow right"
            onClick={() => scrollByPage(1)}
            aria-label={`Scroll ${title} forward`}
          >
            <i className="ph ph-caret-right" aria-hidden="true" />
          </button>
        </>
      )}
      <div className={`row-track ${loops ? "looping" : ""}`} ref={trackRef} role="list">
        {copies.flatMap((copy) =>
          games.map((g) => (
            <GameCase
              key={`${copy}-${g.rawg_id}`}
              game={g}
              inLibrary={libraryIds?.has(g.rawg_id)}
              onPick={onPick}
              clone={copy !== 1}
            />
          ))
        )}
      </div>
    </section>
  );
}
