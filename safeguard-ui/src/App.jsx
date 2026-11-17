import { useState, useEffect, createContext, useContext } from "react";
import { AuthProvider, useAuth } from "./components/Auth";
import { ToastProvider } from "./components/Toast";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Incidents from "./pages/Incidents";
import MediaAnalysis from "./pages/MediaAnalysis";
{/*import Devices from "./pages/Devices";
import Analytics from "./pages/Analytics";*/}
import Users from "./pages/Users";
import AuditLogs from "./pages/AuditLogs";
import SystemStatus from "./pages/SystemStatus";
import Settings from "./pages/Settings";
import { api } from "./api";
import "./index.css";

/* ── Theme Context ─────────────────────────────────────────── */
const ThemeContext = createContext(null);

function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("sg-theme") || "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("sg-theme", theme);
  }, [theme]);

  const toggle = () => setTheme(t => (t === "dark" ? "light" : "dark"));

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

/* ── Theme Toggle Button ───────────────────────────────────── */
function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

/* ── App Shell ─────────────────────────────────────────────── */
function AppShell() {
  const { user, logout } = useAuth();
  const [page, setPage] = useState("dashboard");

  if (!user) return <Login />;

  const MONITOR_PAGES = [
    { id: "dashboard", label: "Dashboard", icon: DashIcon },
    { id: "incidents", label: "Incidents", icon: AlertIcon },
    { id: "media", label: "Media Analysis", icon: VideoIcon },
  ];
  const MANAGE_PAGES = [
    { id: "settings", label: "Settings", icon: GearIcon },
  ];
  const ADMIN_PAGES = [
    { id: "users", label: "Users & Roles", icon: UsersIcon },
    { id: "audit", label: "Audit Logs", icon: LogIcon },
    { id: "status", label: "System Status", icon: StatusIcon },
  ];

  function renderPage() {
    switch (page) {
      case "dashboard": return <Dashboard />;
      case "incidents": return <Incidents />;
      case "media": return <MediaAnalysis />;
      {/*case "devices": return <Devices />;
      case "analytics": return <Analytics />;*/}
      case "settings": return <Settings />;
      case "users": return <Users />;
      case "audit": return <AuditLogs />;
      case "status": return <SystemStatus />;
      default: return <Dashboard />;
    }
  }

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">🛡️</div>
          <div>
            <h1>SafeGuard AI</h1>
            <span>Workplace Safety</span>
          </div>
        </div>
        <div className="sidebar-section">
          <div className="sidebar-section-label">Monitor</div>
          {MONITOR_PAGES.map(p => (
            <button key={p.id} className={`nav-item ${page === p.id ? "active" : ""}`} onClick={() => setPage(p.id)}>
              <p.icon />{p.label}
            </button>
          ))}
        </div>
        <div className="sidebar-section">
          <div className="sidebar-section-label">Manage</div>
          {MANAGE_PAGES.map(p => (
            <button key={p.id} className={`nav-item ${page === p.id ? "active" : ""}`} onClick={() => setPage(p.id)}>
              <p.icon />{p.label}
            </button>
          ))}
        </div>
        <div className="sidebar-section">
          <div className="sidebar-section-label">Admin</div>
          {ADMIN_PAGES.map(p => (
            <button key={p.id} className={`nav-item ${page === p.id ? "active" : ""}`} onClick={() => setPage(p.id)}>
              <p.icon />{p.label}
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="user-pill">
            <div className="user-avatar">{user.username.slice(0,2).toUpperCase()}</div>
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontSize:12,fontWeight:500,color:"var(--text0)",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{user.username}</div>
              <div style={{fontSize:10,color:"var(--text2)"}}>{user.role}</div>
            </div>
            <button onClick={logout} style={{background:"none",border:"none",color:"var(--text2)",cursor:"pointer",fontSize:14,padding:4}} title="Log out">⎋</button>
          </div>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"8px 10px 4px"}}>
            <div style={{display:"flex",alignItems:"center",gap:6}}>
              <span className="status-dot status-online" />
              <span style={{fontSize:11,color:"var(--text2)"}}>System Operational</span>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </nav>

      <div className="main-area">
        <div className="page-content">{renderPage()}</div>
      </div>

    </div>
  );
}

/* ── Root ──────────────────────────────────────────────────── */
export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <AppShell />
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

/* ── Icons ─────────────────────────────────────────────────── */
function DashIcon()   { return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>; }
function AlertIcon()  { return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M8 1L1 13h14L8 1z"/><path d="M8 6v4M8 11.5v.5" strokeLinecap="round"/></svg>; }
function VideoIcon()  { return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="3" width="10" height="10" rx="1.5"/><path d="M11 6l4-2v8l-4-2V6z"/></svg>; }
function GearIcon()   { return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="8" cy="8" r="2.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"/></svg>; }
function UsersIcon()  { return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="6" cy="5" r="2.5"/><path d="M1 14c0-2.76 2.24-5 5-5s5 2.24 5 5"/><circle cx="12" cy="5" r="2"/><path d="M12 10c1.66 0 3 1.34 3 3"/></svg>; }
function LogIcon()    { return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 1h8l3 3v11H3V1z"/><path d="M11 1v3h3"/><path d="M5 7h6M5 10h4"/></svg>; }
function StatusIcon() { return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M1 10l3-6 3 4 2-3 2 3 3-5"/><path d="M1 14h14"/></svg>; }

function SunIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="3"/>
      <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3.22 3.22l1.06 1.06M11.72 11.72l1.06 1.06M3.22 12.78l1.06-1.06M11.72 4.28l1.06-1.06"/>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13.5 10A6 6 0 016 2.5a6 6 0 100 11 6 6 0 007.5-3.5z"/>
    </svg>
  );
}
