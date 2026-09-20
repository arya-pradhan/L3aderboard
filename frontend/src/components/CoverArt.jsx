import { coverSrc } from "../lib/util.js";

// Cover image with a graceful placeholder (RAWG art is often missing).
// The cover box is 2:3 portrait but RAWG art is landscape, so `object-fit:
// cover` scales the image to the box *height*; at ~237px tall that needs a
// ~420px-wide source at 1x — hence srcSet by density rather than card width.
// 640 for 2x is a deliberate bandwidth/sharpness balance: RAWG's next step up
// is 1280 (~5x heavier), and 640 is already ~1.5x density on a retina screen.
export default function CoverArt({ game, score, status, className = "", style }) {
  const url = game && game.cover_url;
  return (
    <div className={`cover ${className}`} style={style}>
      {url ? (
        <img
          src={coverSrc(url, 420)}
          srcSet={`${coverSrc(url, 420)} 1x, ${coverSrc(url, 640)} 2x`}
          alt=""
          loading="lazy"
          decoding="async"
        />
      ) : (
        <span className="cover-fallback">{(game && game.title) || "cover"}</span>
      )}
      {status && <span className={`cover-dot dot-${status}`} aria-hidden="true" />}
      {score != null && score !== "" && score !== "—" && (
        <span className="cover-score" aria-label={`Rated ${score} out of 10`}>
          <i className="ph-fill ph-star" aria-hidden="true" />
          {score}
        </span>
      )}
    </div>
  );
}
