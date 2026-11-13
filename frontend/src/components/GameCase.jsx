import { coverSrc, gameMeta } from "../lib/util.js";

// A game as a CD in its jewel case. Hover/focus slides the disc out
// (the cover art is printed on it). `clone` marks the carousel's looping
// copies: visible, but skipped by keyboard and screen readers.
export default function GameCase({ game, inLibrary, onPick, clone = false }) {
  const art = game.cover_url && coverSrc(game.cover_url, 420);
  const label = inLibrary ? `${game.title}, in your library` : `Open ${game.title}`;
  return (
    <div className="case-cell" aria-hidden={clone || undefined} role={clone ? undefined : "listitem"}>
      <button
        type="button"
        className="case"
        onClick={() => onPick(game)}
        aria-label={label}
        title={game.title}
        tabIndex={clone ? -1 : undefined}
      >
        <span className="disc" aria-hidden="true">
          {art && <img src={art} alt="" loading="lazy" decoding="async" />}
        </span>
        <span className="case-shell" aria-hidden="true">
          <span className="case-art">
            {art ? (
              <img src={art} alt="" loading="lazy" decoding="async" />
            ) : (
              <span className="case-fallback">{game.title}</span>
            )}
          </span>
          {inLibrary && <span className="case-sticker">In library</span>}
        </span>
      </button>
      <span className="case-title">{game.title}</span>
      <span className="case-meta">{gameMeta(game)}</span>
    </div>
  );
}
