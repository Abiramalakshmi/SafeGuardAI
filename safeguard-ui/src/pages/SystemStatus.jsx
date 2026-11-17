import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "../components/Toast";

const ICONS = {
  camera:         "📷",
  audio:          "🎙️",
  visual:         "👁️",
  audio_model:    "🔊",
  emotion:        "🧠",
  aggression:     "⚡",
  database:       "🗄️",
  storage:        "💾",
  torch:          "⚙️",
};

export default function SystemStatus() {
  const toast = useToast();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  async function load() {
    try {
      const res = await api.getStatus();
      setStatus(res);
      setLastRefresh(new Date());
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  // FIX: backend returns objects like {status: "ok"|"warn"|"err", message: "...", detail: "..."}
  // was checking val === true / "online" etc — never matched these objects
  function getState(val) {
    if (!val || typeof val !== "object") return "warning";
    if (val.status === "ok")   return "online";
    if (val.status === "err")  return "offline";
    return "warning"; // covers "warn"
  }

  const entries = status ? Object.entries(status) : [];
  const onlineCount  = entries.filter(([, v]) => getState(v) === "online").length;
  const offlineCount = entries.filter(([, v]) => getState(v) === "offline").length;
  const warnCount    = entries.filter(([, v]) => getState(v) === "warning").length;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">System Status</div>
          <div className="page-sub">
            Real-time component health · {lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : "Loading…"}
          </div>
        </div>
        <button className="btn btn-ghost" onClick={load}>↺ Refresh</button>
      </div>

      {/* Summary */}
      {status && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <SummaryPill label="Online"  count={onlineCount}  color="var(--green)" dimColor="var(--green-dim)" />
          <SummaryPill label="Warning" count={warnCount}    color="var(--amber)" dimColor="var(--amber-dim)" />
          <SummaryPill label="Offline" count={offlineCount} color="var(--red)"   dimColor="var(--red-dim)" />
        </div>
      )}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "var(--text2)" }}>Loading…</div>
      ) : !status ? (
        <div className="empty-state"><p>Could not reach backend</p></div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
          {entries.map(([key, val]) => {
            const state     = getState(val);
            const dotClass  = state === "online"  ? "status-online"  :
                              state === "offline" ? "status-offline" : "status-warning";
            const stateColor = state === "online"  ? "var(--green)"  :
                               state === "offline" ? "var(--red)"    : "var(--amber)";
            const stateLabel = state === "online"  ? "Online"  :
                               state === "offline" ? "Offline" : "Warning";
            const displayName = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
            const icon = ICONS[key] || "🔧";

            return (
              <div
                key={key}
                className="card"
                style={{
                  borderColor: state === "offline" ? "rgba(239,68,68,0.3)" :
                               state === "warning" ? "rgba(245,158,11,0.2)" : "var(--border)",
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 12 }}>{icon}</div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text0)", marginBottom: 4 }}>{displayName}</div>

                {/* Detail label from backend */}
                {val?.detail && (
                  <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 8 }}>{val.detail}</div>
                )}

                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: val?.message ? 8 : 0 }}>
                  <span className={`status-dot ${dotClass}`} />
                  <span style={{ fontSize: 12, color: stateColor, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    {stateLabel}
                  </span>
                </div>

                {/* FIX: was checking typeof val === "string" — now extract from val.message object */}
                {val?.message && (
                  <div style={{ fontSize: 11, color: "var(--text2)", fontFamily: "var(--mono)", lineHeight: 1.5 }}>
                    {val.message}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SummaryPill({ label, count, color, dimColor }) {
  return (
    <div style={{
      background: dimColor,
      border: `1px solid ${color}33`,
      borderRadius: "var(--radius)",
      padding: "8px 16px",
      display: "flex", alignItems: "center", gap: 8,
    }}>
      <span style={{ fontSize: 20, fontWeight: 700, color, fontFamily: "var(--mono)" }}>{count}</span>
      <span style={{ fontSize: 12, color }}>{label}</span>
    </div>
  );
}
