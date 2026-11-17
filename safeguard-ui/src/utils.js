export function riskColor(score) {
  const s = typeof score === "number" ? score : parseFloat(score) || 0;
  if (s >= 0.75) return "var(--red)";
  if (s >= 0.60) return "var(--amber)";
  if (s >= 0.45) return "#fb923c";
  return "var(--green)";
}

export function riskBadgeClass(score) {
  const s = typeof score === "number" ? score : parseFloat(score) || 0;
  if (s >= 0.75) return "badge-red";
  if (s >= 0.60) return "badge-amber";
  if (s >= 0.45) return "badge-amber";
  return "badge-green";
}

export function riskLabel(score) {
  const s = typeof score === "number" ? score : parseFloat(score) || 0;
  if (s >= 0.75) return "CRITICAL";
  if (s >= 0.60) return "HIGH";
  if (s >= 0.45) return "MEDIUM";
  return "LOW";
}

export function levelBadge(level) {
  const map = { UNSAFE: "badge-red", REVIEW: "badge-amber", SAFE: "badge-green" };
  return map[level] || "badge-gray";
}

export function fmtTime(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    });
  } catch { return ts; }
}

export function fmtPct(v) {
  return `${Math.round((parseFloat(v) || 0) * 100)}%`;
}

export function categoryColor(cat) {
  const map = {
    auth: "badge-blue",
    incident: "badge-red",
    device: "badge-cyan",
    settings: "badge-amber",
    user: "badge-gray",
  };
  return map[cat] || "badge-gray";
}
