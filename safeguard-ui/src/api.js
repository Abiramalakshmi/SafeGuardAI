const BASE = "http://localhost:8000";

function getToken() {
  return localStorage.getItem("sg_token");
}

async function req(method, path, body, isForm = false) {
  const headers = {};
  if (!isForm) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  // Auth
  login: (username, password) => req("POST", "/auth/login", { username, password }),
  logout: () => req("POST", "/auth/logout"),

  // Stats & Status
  getStats: () => req("GET", "/stats"),
  getStatus: () => req("GET", "/status"),

  // Incidents
  getIncidents: (params = {}) => {
    const q = new URLSearchParams();
    if (params.level) q.set("level", params.level);
    if (params.source) q.set("source", params.source);
    if (params.date_from) q.set("date_from", params.date_from);
    if (params.date_to) q.set("date_to", params.date_to);
    if (params.limit) q.set("limit", params.limit);
    return req("GET", `/incidents?${q}`);
  },
  resolveIncident: (id) => req("POST", `/incidents/${id}/resolve`),
  clearIncidents: () => req("DELETE", "/incidents"),

  // Devices
  getDevices: () => req("GET", "/devices"),
  addDevice: (d) => req("POST", "/devices", d),
  updateDevice: (id, d) => req("PUT", `/devices/${id}`, d),
  deleteDevice: (id) => req("DELETE", `/devices/${id}`),
  testDevice: (id) => req("POST", `/devices/${id}/test`),

  // Users
  getUsers: () => req("GET", "/users"),
  addUser: (u) => req("POST", "/users", u),
  updateUser: (id, u) => req("PUT", `/users/${id}`, u),
  disableUser: (id) => req("POST", `/users/${id}/disable`),
  enableUser: (id) => req("POST", `/users/${id}/enable`),
  resetPassword: (id, pw) => req("POST", `/users/${id}/reset-password`, { new_password: pw }),
  deleteUser: (id) => req("DELETE", `/users/${id}`),

  // Audit Logs
  getAuditLogs: (params = {}) => {
    const q = new URLSearchParams();
    if (params.category) q.set("category", params.category);
    if (params.user) q.set("user", params.user);
    if (params.limit) q.set("limit", params.limit);
    return req("GET", `/audit-logs?${q}`);
  },
  clearAuditLogs: () => req("DELETE", "/audit-logs"),

  // Settings
  getSettings: () => req("GET", "/settings"),
  saveSettings: (s) => req("POST", "/settings", s),

  // Media Analysis — file upload
  analyzeFile: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return req("POST", "/analyze-video", fd, true);
  },
  analyzeRecording: (blob, filename = "recording.webm") => {
    const fd = new FormData();
    fd.append("file", blob, filename);
    return req("POST", "/analyze-recording", fd, true);
  },

  // Media Analysis — live camera (browser records video+audio blob for 15s)
  analyzeLive: (blob, filename = "live.webm") => {
    const fd = new FormData();
    fd.append("file", blob, filename);
    return req("POST", "/analyze-live", fd, true);
  },
};
