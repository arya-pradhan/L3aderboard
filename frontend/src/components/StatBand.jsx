export default function StatBand({ stats }) {
  const b = stats.byStatus;
  return (
    <div className="stat-band">
      <div className="stat">
        <span className="num">{stats.total}</span>
        <span className="lbl">Games logged</span>
        <span className="sub">
          {b.completed} completed · {b.backlog} backlog · {b.dropped} dropped
        </span>
      </div>
      <div className="stat">
        <span className="num">
          {Math.round(stats.hours).toLocaleString()}
          <small> hrs</small>
        </span>
        <span className="lbl">Hours played</span>
        <span className="sub">
          {stats.total ? `${(stats.hours / stats.total).toFixed(1)} hrs avg per game` : "—"}
        </span>
      </div>
      <div className="stat">
        <span className="num">{stats.reviews}</span>
        <span className="lbl">Reviews written</span>
        <span className="sub">
          {stats.avgRating != null ? `avg rating ${stats.avgRating.toFixed(1)} / 10` : "no ratings yet"}
        </span>
      </div>
    </div>
  );
}
