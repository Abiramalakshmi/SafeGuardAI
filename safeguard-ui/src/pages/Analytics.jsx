import { useEffect, useState } from "react";
import { api } from "../api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from "recharts";

export default function Analytics() {
  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getIncidents({ limit: 500 }), api.getStats()])
      .then(([inc, s]) => {
        setIncidents(inc.incidents || []);
        setStats(s);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, color: "var(--text2)" }}>Loading…</div>;

  const byDay      = buildByDay(incidents);
  const bySource   = buildBySource(incidents);
  const byEmotion  = buildByEmotion(incidents);
  const scoreTrend = buildScoreTrend(incidents);

  const COLORS = ["#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6"];

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Analytics & Reports</div>
          <div className="page-sub">Insights from {incidents.length} recorded incidents</div>
        </div>
      </div>

      {/* Summary stats */}
      {stats && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          {[
            { label: "Total",    value: stats.total,    color: "var(--accent)" },
            { label: "Unsafe",   value: stats.unsafe,   color: "var(--red)"   },
            { label: "Review",   value: stats.review,   color: "var(--amber)" },
            { label: "Resolved", value: stats.resolved, color: "var(--green)" },
          ].map(s => (
            <div key={s.label} style={{
              background: "var(--bg1)", border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)", padding: "12px 20px", flex: 1,
            }}>
              <div style={{ fontSize: 10, color: "var(--text2)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 24, fontWeight: 600, color: s.color, fontFamily: "var(--mono)" }}>{s.value ?? "—"}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 14 }}>Incidents per Day</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={byDay}>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--text2)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "var(--text2)" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border2)", borderRadius: 8, fontSize: 11 }} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar dataKey="count" fill="var(--accent)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 14 }}>Risk Score Trend</div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={scoreTrend}>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--text2)" }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 1]} tickFormatter={v => `${Math.round(v * 100)}%`} tick={{ fontSize: 10, fill: "var(--text2)" }} axisLine={false} tickLine={false} />
              <Tooltip formatter={v => `${Math.round(v * 100)}%`} contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border2)", borderRadius: 8, fontSize: 11 }} />
              <Line type="monotone" dataKey="avg" stroke="var(--red)" strokeWidth={2} dot={{ fill: "var(--red)", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 14 }}>Top Incident Sources</div>
          {bySource.length === 0 ? (
            <div className="empty-state" style={{ padding: "20px 0" }}><p>No data</p></div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {bySource.slice(0, 8).map((s, i) => (
                <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ width: 18, fontSize: 12, color: "var(--text2)", fontFamily: "var(--mono)" }}>{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: "var(--text0)", marginBottom: 4 }}>{s.name}</div>
                    <div style={{ height: 4, background: "var(--bg4)", borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ width: `${Math.round((s.count / bySource[0].count) * 100)}%`, height: "100%", background: "var(--accent)", borderRadius: 2 }} />
                    </div>
                  </div>
                  <span style={{ fontSize: 12, color: "var(--text1)", fontFamily: "var(--mono)", minWidth: 24, textAlign: "right" }}>{s.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 14 }}>Emotion Distribution</div>
          {byEmotion.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={byEmotion}
                  dataKey="count"
                  nameKey="emotion"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  label={({ emotion, percent }) => `${emotion} ${Math.round(percent * 100)}%`}
                  labelLine={false}
                  fontSize={10}
                >
                  {byEmotion.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border2)", borderRadius: 8, fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding: "20px 0" }}><p>No emotion data yet</p></div>
          )}
        </div>
      </div>
    </div>
  );
}

function buildByDay(incidents) {
  const map = {};
  incidents.forEach(i => {
    const d = (i.timestamp || "").slice(0, 10);
    if (d) map[d] = (map[d] || 0) + 1;
  });
  return Object.entries(map)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([date, count]) => ({ date: date.slice(5), count }));
}

function buildBySource(incidents) {
  const map = {};
  incidents.forEach(i => {
    const s = i.video_source || "Unknown";
    map[s] = (map[s] || 0) + 1;
  });
  return Object.entries(map)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

function buildByEmotion(incidents) {
  const map = {};
  incidents.forEach(i => {
    // FIX: was i.emotion — backend stores as emotion_detected in the incidents table
    // fall back to i.emotion in case the API enriches it
    const e = i.emotion_detected || i.emotion;
    if (e) map[e] = (map[e] || 0) + 1;
  });
  return Object.entries(map)
    .map(([emotion, count]) => ({ emotion, count }))
    .sort((a, b) => b.count - a.count);
}

function buildScoreTrend(incidents) {
  const map = {};
  incidents.forEach(i => {
    const d = (i.timestamp || "").slice(0, 10);
    const s = parseFloat(i.violence_score) || 0;
    if (d) {
      if (!map[d]) map[d] = { sum: 0, count: 0 };
      map[d].sum   += s;
      map[d].count += 1;
    }
  });
  return Object.entries(map)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([date, { sum, count }]) => ({ date: date.slice(5), avg: Math.round((sum / count) * 100) / 100 }));
}
