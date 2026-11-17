import { useEffect, useState } from "react";
import { api } from "../api";
import { categoryColor, fmtTime } from "../utils";
import { useToast } from "../components/Toast";

const CATEGORIES = ["", "auth", "incident", "device", "settings", "user"];

export default function AuditLogs() {
  const toast = useToast();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");

  async function load() {
    setLoading(true);
    try {
      const res = await api.getAuditLogs({ category: category || undefined, limit: 300 });
      setLogs(res.logs || []);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [category]);

  async function handleClear() {
    if (!confirm("Clear all audit logs?")) return;
    try {
      await api.clearAuditLogs();
      toast("Audit logs cleared", "success");
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  const filtered = search
    ? logs.filter(l =>
        l.user?.toLowerCase().includes(search.toLowerCase()) ||
        l.action?.toLowerCase().includes(search.toLowerCase()) ||
        l.target?.toLowerCase().includes(search.toLowerCase())
      )
    : logs;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Audit Logs</div>
          <div className="page-sub">Track all user activity and system events</div>
        </div>
        <button className="btn btn-danger btn-sm" onClick={handleClear}>Clear Logs</button>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <input
          className="input"
          style={{ width: 240 }}
          placeholder="Search logs…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className="input" style={{ width: 140 }} value={category} onChange={e => setCategory(e.target.value)}>
          {CATEGORIES.map(c => <option key={c} value={c}>{c || "All Categories"}</option>)}
        </select>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text2)" }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state"><p>No logs found</p></div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Category</th>
                  <th>Time</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((log, i) => (
                  <tr key={i}>
                    <td style={{ color: "var(--text0)", fontWeight: 500 }}>{log.user}</td>
                    <td>{log.action}</td>
                    <td style={{ color: "var(--text1)", fontFamily: "var(--mono)", fontSize: 11 }}>{log.target || "—"}</td>
                    <td><span className={`badge ${categoryColor(log.category)}`}>{log.category}</span></td>
                    <td style={{ fontFamily: "var(--mono)", fontSize: 11 }}>{fmtTime(log.timestamp)}</td>
                    <td style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)" }}>{log.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
