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
  let reviews = 0;
  let ratingSum = 0;
  let rated = 0;
  for (const e of entries) {
    byStatus[e.status] = (byStatus[e.status] || 0) + 1;
    hours += e.hours_played || 0;
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
    reviews,
    avgRating: rated ? ratingSum / rated : null,
  };
}

// year · genre1 · genre2  — the small meta line under a game title
export function gameMeta(game, extra) {
  const bits = [];
  if (game.release_date) bits.push(String(game.release_date).slice(0, 4));
  (game.genres || []).slice(0, 2).forEach((g) => bits.push(g));
  if (extra) bits.push(extra);
  return bits.join(" · ");
}
