// Cover image with a graceful placeholder (RAWG art is often missing).
export default function CoverArt({ game, score, status, className = "", style }) {
  const url = game && game.cover_url;
  return (
    <div className={`cover ${className}`} style={style}>
      {url ? (
        <img src={url} alt={game.title} loading="lazy" />
      ) : (
        <span className="cover-fallback">{(game && game.title) || "cover"}</span>
      )}
      {status && <span className={`cover-dot dot-${status}`} />}
      {score != null && score !== "" && score !== "—" && (
        <span className="cover-score">{score}</span>
      )}
    </div>
  );
}
