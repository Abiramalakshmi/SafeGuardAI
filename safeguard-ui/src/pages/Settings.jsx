import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "../components/Toast";

const DEFAULTS = {
  auto_archive_days: 30,
  timezone: "UTC",
  datetime_format: "24h",
  audit_log_retention_days: 90,
};

export default function Settings() {
  const toast = useToast();
  const [settings, setSettings] = useState(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getSettings()
      .then(s => {
        const coerced = { ...DEFAULTS, ...s };
        setSettings(coerced);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function set(key, val) {
    setSettings(s => ({ ...s, [key]: val }));
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.saveSettings({
        auto_archive_days:        parseInt(settings.auto_archive_days),
        timezone:                 settings.timezone,
        datetime_format:          settings.datetime_format,
        audit_log_retention_days: parseInt(settings.audit_log_retention_days),
      });
      toast("Settings saved", "success");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div style={{ padding: 40, color: "var(--text2)" }}>Loading…</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Settings</div>
          <div className="page-sub">Incident management and system preferences</div>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving…" : "Save Changes"}
        </button>
      </div>

      <div className="grid-2">

        {/* Incident Management */}
        <div className="card">
          <SectionTitle>Incident Management</SectionTitle>

          <div className="form-group">
            <label className="form-label">Auto-Archive Incidents After</label>
            <SelectNumber
              value={settings.auto_archive_days}
              onChange={v => set("auto_archive_days", v)}
              options={[7, 14, 30, 60, 90, 180]}
              unit="days"
            />
            <FieldHint>Resolved incidents older than this will be archived automatically.</FieldHint>
          </div>
        </div>

        {/* System */}
        <div className="card">
          <SectionTitle>System</SectionTitle>

          <div className="form-group">
            <label className="form-label">Timezone</label>
            <select
              className="input"
              value={settings.timezone}
              onChange={e => set("timezone", e.target.value)}
            >
              {[
                "UTC",
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "Europe/London",
                "Europe/Paris",
                "Europe/Berlin",
                "Asia/Kolkata",
                "Asia/Tokyo",
                "Asia/Singapore",
                "Australia/Sydney",
              ].map(tz => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
            <FieldHint>Used for displaying timestamps across the app.</FieldHint>
          </div>

          <div className="form-group" style={{ marginTop: 14 }}>
            <label className="form-label">Date &amp; Time Format</label>
            <select
              className="input"
              value={settings.datetime_format}
              onChange={e => set("datetime_format", e.target.value)}
            >
              <option value="24h">24-hour (14:30)</option>
              <option value="12h">12-hour (2:30 PM)</option>
            </select>
          </div>

          <Divider />

          <div className="form-group">
            <label className="form-label">Audit Log Retention</label>
            <SelectNumber
              value={settings.audit_log_retention_days}
              onChange={v => set("audit_log_retention_days", v)}
              options={[30, 60, 90, 180, 365]}
              unit="days"
            />
            <FieldHint>Audit entries older than this will be permanently deleted.</FieldHint>
          </div>
        </div>

      </div>
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text0)", marginBottom: 18 }}>
      {children}
    </div>
  );
}

function FieldHint({ children }) {
  return (
    <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 5 }}>{children}</div>
  );
}

function Divider() {
  return <div style={{ borderTop: "1px solid var(--border)", margin: "16px 0" }} />;
}

function SelectNumber({ value, onChange, options, unit }) {
  return (
    <select
      className="input"
      value={value}
      onChange={e => onChange(parseInt(e.target.value))}
    >
      {options.map(o => (
        <option key={o} value={o}>{o} {unit}</option>
      ))}
    </select>
  );
}
