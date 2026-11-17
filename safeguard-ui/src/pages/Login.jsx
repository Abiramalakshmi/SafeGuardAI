import { useState } from "react";
import { useAuth } from "../components/Auth";
import { useToast } from "../components/Toast";

export default function Login() {
  const { login } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState({ username: "", password: "" });
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(form.username, form.password);
    } catch (err) {
      toast(err.message || "Login failed", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <div style={{ width: 40, height: 40, background: "var(--accent)", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>🛡️</div>
          <div>
            <h2>SafeGuard AI</h2>
            <p style={{ margin: 0 }}>Sign in to your account</p>
          </div>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              className="input"
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              placeholder="admin"
              autoFocus
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="input"
              type="password"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary w-full"
            disabled={loading}
            style={{ width: "100%", justifyContent: "center", marginTop: 8, padding: "10px" }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div style={{ marginTop: 20, padding: "12px 14px", background: "var(--bg2)", borderRadius: "var(--radius)", fontSize: 12, color: "var(--text2)" }}>
          Default: <span className="text-mono" style={{ color: "var(--text1)" }}>admin / admin123</span>
        </div>
      </div>
    </div>
  );
}
