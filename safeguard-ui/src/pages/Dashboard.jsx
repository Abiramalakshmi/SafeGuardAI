import { useEffect, useState } from "react";
import { api } from "../api";
import { riskColor, levelBadge, fmtTime } from "../utils";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getStats(), api.getIncidents({ limit: 200 })])
      .then(([s, inc]) => {
        setStats(s);
        setIncidents(inc.incidents || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const chartData = buildMultiLineData(incidents);
  const recentAlerts = incidents.slice(0, 5);

  if (loading) return <div style={{ padding: 40, color: "var(--text2)" }}>Loading…</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Security Overview</div>
          <div className="page-sub">Real-time threat monitoring</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="status-dot status-online" />
          <span style={{ fontSize: 12, color: "var(--green)" }}>Live</span>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Unsafe Incidents"
          value={stats?.unsafe ?? "—"}
          sub="Require immediate action"
          color="var(--red)"
        />
        <StatCard
          label="Under Review"
          value={stats?.review ?? "—"}
          sub="Awaiting investigation"
          color="var(--amber)"
        />
        <StatCard
          label="Resolved"
          value={stats?.resolved ?? "—"}
          sub="Closed incidents"
          color="var(--green)"
        />
        <StatCard
          label="Total Analyses"
          value={stats?.total ?? "—"}
          sub="All time"
          color="var(--accent)"
        />
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* Recent alerts */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 14, display: "flex", justifyContent: "space-between" }}>
            <span>Latest Alerts</span>
            {incidents.filter(i => i.alert_level === "UNSAFE").length > 0 && (
              <span className="badge badge-red">{incidents.filter(i => i.alert_level === "UNSAFE").length} Critical</span>
            )}
          </div>
          {recentAlerts.length === 0 ? (
            <div className="empty-state" style={{ padding: "20px 0" }}><p>No incidents yet</p></div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {recentAlerts.map(inc => (
                <AlertRow key={inc.incident_id || inc.id} inc={inc} />
              ))}
            </div>
          )}
        </div>

        {/* Multi-line Chart */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 4 }}>
            Incidents Over Time
          </div>
          <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 14 }}>
            Last 7 days — daily counts by category
          </div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: "var(--text2)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: "var(--text2)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg2)",
                    border: "1px solid var(--border2)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  cursor={{ stroke: "var(--text2)", strokeWidth: 1, strokeDasharray: "4 2" }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                  iconType="circle"
                  iconSize={8}
                />
                <Line
                  type="monotone"
                  dataKey="Unsafe"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#ef4444", strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="Review"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#f59e0b", strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="Safe"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#22c55e", strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding: "20px 0" }}><p>No data yet</p></div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-sub">{sub}</div>
    </div>
  );
}

function AlertRow({ inc }) {
  const score = parseFloat(inc.violence_score) || 0;
  const isHigh = inc.alert_level === "UNSAFE";
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 12px", borderRadius: "var(--radius)",
      background: isHigh ? "rgba(239,68,68,0.06)" : "var(--bg2)",
      border: `1px solid ${isHigh ? "rgba(239,68,68,0.2)" : "var(--border)"}`,
    }}>
      <div>
        <div style={{ fontSize: 13, color: "var(--text0)", fontWeight: 500 }}>
          {inc.video_source || "Unknown source"}
        </div>
        <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 2 }}>
          {fmtTime(inc.timestamp)}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: riskColor(score), fontFamily: "var(--mono)" }}>
          {Math.round(score * 100)}%
        </span>
        <span className={`badge ${levelBadge(inc.alert_level)}`}>{inc.alert_level}</span>
      </div>
    </div>
  );
}

function buildMultiLineData(incidents) {
  // Build last 7 days as keys
  const days = {};
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    days[key] = { date: key, Unsafe: 0, Review: 0, Safe: 0 };
  }

  incidents.forEach(inc => {
    if (!inc.timestamp) return;
    const d = new Date(inc.timestamp);
    const key = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    if (!days[key]) return;

    const level = (inc.alert_level || "").toUpperCase();
    if (level === "UNSAFE") {
      days[key].Unsafe++;
    } else if (level === "REVIEW") {
      days[key].Review++;
    } else if (level === "SAFE") {
      days[key].Safe++;
    }
  });

  return Object.values(days);
}
