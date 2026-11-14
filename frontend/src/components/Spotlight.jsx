import { useState } from "react";
import { coverSrc, gameMeta } from "../lib/util.js";

// The Discover hero: a CD changer loaded with this year's most popular games.
// One disc spins in the tray; the transport buttons swap it, and the LCD
// says which disc is in. Nothing advances on its own.
export default function Spotlight({ title, games, library, onOpen }) {
  const [i, setI] = useState(0);
  const g = games[i];
  const art = coverSrc(g.cover_url, 1280);
  const step = (d) => setI((i + d + games.length) % games.length);

  return (
    <section className="spot" aria-label="Featured games">
      <div className="spot-bg" aria-hidden="true">
        {art && <img key={g.rawg_id} src={art} alt="" />}
      </div>

      <div className="spot-copy">
        <p className="spot-label">{title}</p>
        <h1 className="spot-title">{g.title}</h1>
        <p className="spot-meta">{gameMeta(g) || "Release date to be announced"}</p>
        <div className="spot-controls">
          <button className="btn primary" onClick={() => onOpen(g)}>
            {library.has(g.rawg_id) ? "Open your log" : "Open game"}
          </button>
          <div className="spot-transport" role="group" aria-label="Change featured game">
            <button className="arcade-key" onClick={() => step(-1)} aria-label="Previous game">
              <i className="ph ph-skip-back" aria-hidden="true" />
            </button>
            <output className="lcd" aria-live="polite">
              Disc {i + 1} of {games.length}
            </output>
            <button className="arcade-key" onClick={() => step(1)} aria-label="Next game">
              <i className="ph ph-skip-forward" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <div className="spot-player" aria-hidden="true">
        <div className="spot-tray">
          <span className="disc spot-disc" key={g.rawg_id}>
            {art && <img src={coverSrc(g.cover_url, 640)} alt="" />}
          </span>
        </div>
      </div>
    </section>
  );
}
