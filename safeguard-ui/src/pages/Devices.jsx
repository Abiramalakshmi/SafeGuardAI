import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "../components/Toast";

const EMPTY = { name: "", location: "", rtspUrl: "", type: "camera", enabled: true };

export default function Devices() {
  const toast = useToast();
  const [devices, setDevices] = useState([]);
  const [modal, setModal] = useState(null); // null | "add" | {id, ...}
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(null);

  async function load() {
    try {
      const res = await api.getDevices();
      setDevices(res.devices || []);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function openAdd() { setForm(EMPTY); setModal("add"); }
  function openEdit(d) { setForm({ name: d.name, location: d.location, rtspUrl: d.rtspUrl, type: d.type, enabled: d.enabled }); setModal(d); }

  async function handleSave() {
    try {
      if (modal === "add") {
        await api.addDevice(form);
        toast("Device added", "success");
      } else {
        await api.updateDevice(modal.id, form);
        toast("Device updated", "success");
      }
      setModal(null);
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this device?")) return;
    try {
      await api.deleteDevice(id);
      toast("Device removed", "success");
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function handleTest(id) {
    setTesting(id);
    try {
      const res = await api.testDevice(id);
      toast(res.ok ? "Device is online!" : "Device is offline", res.ok ? "success" : "error");
      load();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setTesting(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Devices & Cameras</div>
          <div className="page-sub">{devices.filter(d => d.status === "online").length} online · {devices.length} total</div>
        </div>
        <button className="btn btn-primary" onClick={openAdd}>+ Add Device</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text2)" }}>Loading…</div>
        ) : devices.length === 0 ? (
          <div className="empty-state"><p>No devices configured</p></div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Device</th>
                  <th>Location</th>
                  <th>Type</th>
                  <th>Stream URL</th>
                  <th>Status</th>
                  <th>Last Seen</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {devices.map(d => (
                  <tr key={d.id}>
                    <td style={{ color: "var(--text0)", fontWeight: 500 }}>{d.name}</td>
                    <td>{d.location}</td>
                    <td><span className="badge badge-blue">{d.type}</span></td>
                    <td>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text2)" }}>
                        {d.rtspUrl?.slice(0, 36)}{d.rtspUrl?.length > 36 ? "…" : ""}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span className={`status-dot ${d.status === "online" ? "status-online" : "status-offline"}`} />
                        <span style={{ fontSize: 12, color: d.status === "online" ? "var(--green)" : "var(--red)" }}>
                          {d.status || "unknown"}
                        </span>
                      </div>
                    </td>
                    <td style={{ fontSize: 12 }}>{d.lastSeen || "—"}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        <button className="btn btn-ghost btn-sm" onClick={() => handleTest(d.id)} disabled={testing === d.id}>
                          {testing === d.id ? "…" : "Test"}
                        </button>
                        <button className="btn btn-ghost btn-sm" onClick={() => openEdit(d)}>Edit</button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(d.id)}>Del</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">
              {modal === "add" ? "Add Device" : "Edit Device"}
              <button className="btn btn-ghost btn-sm" onClick={() => setModal(null)}>✕</button>
            </div>
            <div className="form-group">
              <label className="form-label">Name</label>
              <input className="input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Camera #8" />
            </div>
            <div className="form-group">
              <label className="form-label">Location</label>
              <input className="input" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} placeholder="Warehouse — Building B" />
            </div>
            <div className="form-group">
              <label className="form-label">Stream URL (RTSP / Audio)</label>
              <input className="input" value={form.rtspUrl} onChange={e => setForm(f => ({ ...f, rtspUrl: e.target.value }))} placeholder="rtsp://192.168.1.108:554/stream1" style={{ fontFamily: "var(--mono)", fontSize: 12 }} />
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="input" value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
                  <option value="camera">Camera</option>
                  <option value="microphone">Microphone</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Enabled</label>
                <div style={{ paddingTop: 8 }}>
                  <button
                    className={`toggle ${form.enabled ? "on" : ""}`}
                    onClick={() => setForm(f => ({ ...f, enabled: !f.enabled }))}
                  />
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
              <button className="btn btn-ghost" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
