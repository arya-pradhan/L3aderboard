export const STATUSES = ["playing", "completed", "dropped", "backlog"];

export function initials(name) {
  if (!name) return "?";
  const parts = name.replace(/[^a-zA-Z0-9]+/g, " ").trim().split(/\s+/);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export function fmtHours(h) {
  const n = Number(h) || 0;
  return `${n % 1 === 0 ? n : n.toFixed(1)} hrs`;
}

export function statusLabel(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
}

export function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export function timeAgo(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return "just now";
  const m = s / 60;
  if (m < 60) return `${Math.floor(m)}m ago`;
  const h = m / 60;
  if (h < 24) return `${Math.floor(h)}h ago`;
  const days = h / 24;
  if (days < 30) return `${Math.floor(days)}d ago`;
  return d.toLocaleDateString();
}

export function computeStats(entries) {
  const byStatus = { playing: 0, completed: 0, dropped: 0, backlog: 0 };
  let hours = 0;
  let played = 0; // entries with any hours — unplayed backlog shouldn't drag the avg down
  let reviews = 0;
  let ratingSum = 0;
  let rated = 0;
  for (const e of entries) {
    byStatus[e.status] = (byStatus[e.status] || 0) + 1;
    const h = e.hours_played || 0;
    if (h > 0) {
      hours += h;
      played += 1;
    }
    if (e.review_text) reviews += 1;
    if (e.rating != null) {
      ratingSum += e.rating;
      rated += 1;
    }
  }
  return {
    total: entries.length,
    byStatus,
    hours,
    played,
    avgHours: played ? hours / played : null,
    reviews,
    avgRating: rated ? ratingSum / rated : null,
  };
}

/**
 * RAWG's `background_image` is a full-size (~1920px) landscape screenshot.
 * RAWG also serves resized variants; requesting one sized for the slot avoids
 * a heavy in-browser downscale (which reads as "soft") and loads far faster.
 * Non-RAWG or already-resized URLs pass through untouched.
 */
export function coverSrc(url, width = 640) {
  if (!url) return url;
  const marker = "media.rawg.io/media/";
  const i = url.indexOf(marker);
  if (i === -1 || url.includes("/media/resize/") || url.includes("/media/crop/")) {
    return url;
  }
  const cut = i + marker.length;
  return `${url.slice(0, cut)}resize/${width}/-/${url.slice(cut)}`;
}

// year · genre1 · genre2  — the small meta line under a game title
export function gameMeta(game, extra) {
  const bits = [];
  if (game.release_date) bits.push(String(game.release_date).slice(0, 4));
  (game.genres || []).slice(0, 2).forEach((g) => bits.push(g));
  if (extra) bits.push(extra);
  return bits.join(" · ");
}
