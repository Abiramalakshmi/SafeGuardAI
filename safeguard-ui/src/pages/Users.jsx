import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "../components/Toast";

const EMPTY = { name: "", email: "", role: "viewer", password: "" };
const ROLES = ["admin", "security_operator", "investigator", "viewer"];

export default function Users() {
  const toast = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [resetPw, setResetPw] = useState(null);

  async function load() {
    try {
      const res = await api.getUsers();
      setUsers(res.users || []);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function openAdd() { setForm(EMPTY); setModal("add"); }
  function openEdit(u) { setForm({ name: u.name, email: u.email, role: u.role, password: "" }); setModal(u); }

  async function handleSave() {
    try {
      if (modal === "add") {
        const res = await api.addUser(form);
        if (res.generated_password) toast(`Generated password: ${res.generated_password}`, "info");
        else toast("User created", "success");
      } else {
        await api.updateUser(modal.id, { name: form.name, email: form.email, role: form.role });
        toast("User updated", "success");
      }
      setModal(null);
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function toggleStatus(u) {
    try {
      if (u.status === "disabled") await api.enableUser(u.id);
      else await api.disableUser(u.id);
      toast(`User ${u.status === "disabled" ? "enabled" : "disabled"}`, "success");
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function handleDelete(u) {
    if (!confirm(`Delete ${u.name}?`)) return;
    try {
      await api.deleteUser(u.id);
      toast("User deleted", "success");
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function handleResetPw(u) {
    try {
      const res = await api.resetPassword(u.id, null);
      setResetPw({ user: u.name, password: res.new_password });
    } catch (e) {
      toast(e.message, "error");
    }
  }

  function roleBadge(role) {
    const map = { admin: "badge-red", security_operator: "badge-amber", investigator: "badge-blue", viewer: "badge-gray" };
    return map[role] || "badge-gray";
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Users & Roles</div>
          <div className="page-sub">{users.filter(u => u.status !== "disabled").length} active users</div>
        </div>
        <button className="btn btn-primary" onClick={openAdd}>+ Add User</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text2)" }}>Loading…</div>
        ) : users.length === 0 ? (
          <div className="empty-state"><p>No users found</p></div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{
                        width: 30, height: 30, borderRadius: "50%", background: "var(--accent)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 11, fontWeight: 600, color: "white", flexShrink: 0,
                        opacity: u.status === "disabled" ? 0.4 : 1,
                      }}>
                        {(u.name || "?").slice(0, 2).toUpperCase()}
                      </div>
                      <span style={{ color: "var(--text0)", fontWeight: 500 }}>{u.name}</span>
                    </div>
                  </td>
                  <td style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{u.email}</td>
                  <td><span className={`badge ${roleBadge(u.role)}`}>{u.role}</span></td>
                  <td>
                    <span className={`badge ${u.status === "disabled" ? "badge-gray" : "badge-green"}`}>
                      {u.status || "active"}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      <button className="btn btn-ghost btn-sm" onClick={() => handleResetPw(u)}>Reset PW</button>
                      <button className="btn btn-ghost btn-sm" onClick={() => toggleStatus(u)}>
                        {u.status === "disabled" ? "Enable" : "Disable"}
                      </button>
                      <button className="btn btn-ghost btn-sm" onClick={() => openEdit(u)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(u)}>Del</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">
              {modal === "add" ? "Add User" : "Edit User"}
              <button className="btn btn-ghost btn-sm" onClick={() => setModal(null)}>✕</button>
            </div>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input className="input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="John Smith" />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input className="input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} placeholder="j.smith@company.com" />
            </div>
            <div className="form-group">
              <label className="form-label">Role</label>
              <select className="input" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            {modal === "add" && (
              <div className="form-group">
                <label className="form-label">Password (leave blank to auto-generate)</label>
                <input className="input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="auto-generated" />
              </div>
            )}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="btn btn-ghost" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave}>Save</button>
            </div>
          </div>
        </div>
      )}

      {resetPw && (
        <div className="modal-overlay" onClick={() => setResetPw(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🔑</div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8, color: "var(--text0)" }}>Password Reset</div>
            <div style={{ fontSize: 13, color: "var(--text2)", marginBottom: 16 }}>New password for {resetPw.user}:</div>
            <div style={{ background: "var(--bg2)", padding: "12px 16px", borderRadius: "var(--radius)", fontFamily: "var(--mono)", fontSize: 16, fontWeight: 600, color: "var(--accent)", marginBottom: 16 }}>
              {resetPw.password}
            </div>
            <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 20 }}>Copy this password — it won't be shown again</div>
            <button className="btn btn-primary" onClick={() => setResetPw(null)}>Done</button>
          </div>
        </div>
      )}
    </div>
  );
}
