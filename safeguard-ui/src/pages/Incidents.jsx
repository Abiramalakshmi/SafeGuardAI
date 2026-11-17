import { useEffect, useState } from "react";
import { api } from "../api";
import { levelBadge, fmtTime, fmtPct, riskColor } from "../utils";
import { useToast } from "../components/Toast";

// ---------------------------------------------------------------------------
// Lightweight in-memory comment store (keyed by incident id).
// Replace with api.getComments / api.addComment if you wire a backend.
// ---------------------------------------------------------------------------
const commentStore = {};
function getComments(id) { return commentStore[id] ? [...commentStore[id]] : []; }
function addComment(id, comment) {
  if (!commentStore[id]) commentStore[id] = [];
  commentStore[id].push(comment);
}

export default function Incidents() {
  const toast = useToast();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ level: "", source: "" });
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const res = await api.getIncidents({ level: filters.level || undefined, limit: 200 });
      setIncidents(res.incidents || []);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filters.level]);

  async function handleResolve(id, e) {
    e.stopPropagation();
    try {
      await api.resolveIncident(id);
      toast("Incident resolved", "success");
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function handleClearAll() {
    if (!confirm("Clear all incidents? This cannot be undone.")) return;
    try {
      await api.clearIncidents();
      toast("All incidents cleared", "success");
      load();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  const filtered = filters.source
    ? incidents.filter(i => i.video_source?.toLowerCase().includes(filters.source.toLowerCase()))
    : incidents;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Incidents</div>
          <div className="page-sub">{filtered.length} records</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-danger btn-sm" onClick={handleClearAll}>Clear All</button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <select
          className="input"
          style={{ width: 140 }}
          value={filters.level}
          onChange={e => setFilters(f => ({ ...f, level: e.target.value }))}
        >
          <option value="">All Levels</option>
          <option value="UNSAFE">Unsafe</option>
          <option value="REVIEW">Review</option>
          <option value="SAFE">Safe</option>
        </select>
        <input
          className="input"
          style={{ width: 200 }}
          placeholder="Filter by source…"
          value={filters.source}
          onChange={e => setFilters(f => ({ ...f, source: e.target.value }))}
        />
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text2)" }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state"><p>No incidents found</p></div>
        ) : (
          <div>
            {filtered.map(inc => (
              <IncidentRow
                key={inc.incident_id || inc.id}
                inc={inc}
                expanded={expanded === (inc.incident_id || inc.id)}
                onToggle={() => {
                  const id = inc.incident_id || inc.id;
                  setExpanded(expanded === id ? null : id);
                }}
                onResolve={handleResolve}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// IncidentRow
// ---------------------------------------------------------------------------
function IncidentRow({ inc, expanded, onToggle, onResolve }) {
  const score = parseFloat(inc.violence_score) || 0;
  const isUnsafe = inc.alert_level === "UNSAFE";
  const isReview = inc.alert_level === "REVIEW";
  const incId = inc.incident_id || inc.id;

  return (
    <div
      style={{
        borderBottom: "1px solid var(--border)",
        borderLeft: `3px solid ${isUnsafe ? "var(--red)" : isReview ? "var(--amber)" : "transparent"}`,
      }}
    >
      <div
        style={{ display: "flex", alignItems: "center", padding: "12px 16px", cursor: "pointer", gap: 12 }}
        onClick={onToggle}
      >
        <span className={`badge ${levelBadge(inc.alert_level)}`} style={{ minWidth: 60, justifyContent: "center" }}>
          {inc.alert_level}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text0)", marginBottom: 2 }}>
            {inc.video_source || "Unknown"}
          </div>
          <div style={{ fontSize: 11, color: "var(--text2)" }}>{fmtTime(inc.timestamp)}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexShrink: 0 }}>
          <ScoreBar label="Violence" value={score} />
          {inc.alert_level !== "SAFE" && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={(e) => onResolve(incId, e)}
            >
              Resolve
            </button>
          )}
          <span style={{ color: "var(--text2)", fontSize: 12 }}>{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ padding: "0 16px 16px" }}>
          {/* Core info grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
            <InfoCell label="Violence Score"   value={fmtPct(inc.violence_score)} />
            <InfoCell label="Toxicity Score"   value={fmtPct(inc.toxicity_score)} />
            <InfoCell label="Aggression Score" value={fmtPct(inc.aggression_score)} />
            <InfoCell label="Emotion"          value={(inc.emotion_detected || inc.emotion || "—")} />
            <InfoCell
              label="Toxic Speech"
              value={inc.is_speech_aggressive ? "Detected" : "None"}
              highlight={!!inc.is_speech_aggressive}
            />
            <InfoCell label="Source"     value={inc.video_source || "—"} />
            <InfoCell label="Status"     value={inc.status || "OPEN"} />
            <InfoCell label="Alert Level" value={inc.alert_level || "—"} />
          </div>

          {/* VIDEO CLIP */}
          {inc.clip_path && (
            <div style={{ marginBottom: 16 }}>
              <SectionLabel>Incident Clip</SectionLabel>
              <video
                controls
                style={{
                  width: "100%",
                  maxHeight: 360,
                  borderRadius: "var(--radius)",
                  background: "#000",
                  display: "block",
                }}
                src={`http://localhost:8000${inc.clip_path}`}
              >
                Your browser does not support the video tag.
              </video>
            </div>
          )}

          {/* TRANSCRIPT */}
          {inc.transcript && (
            <div style={{ marginBottom: 16 }}>
              <SectionLabel>Transcript</SectionLabel>
              <div style={{
                background: "var(--bg2)", borderRadius: "var(--radius)",
                padding: "10px 12px", fontSize: 12, color: "var(--text1)",
                fontFamily: "var(--mono)", lineHeight: 1.6, whiteSpace: "pre-wrap"
              }}>
                {inc.transcript}
              </div>
            </div>
          )}

          {/* TOXIC PHRASES */}
          {inc.toxic_phrases?.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <SectionLabel>Toxic Phrases</SectionLabel>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {inc.toxic_phrases.map((p, i) => (
                  <span key={i} className="badge badge-red">{p}</span>
                ))}
              </div>
            </div>
          )}

          {/* INVESTIGATION PANEL — REVIEW only */}
          {isReview && (
            <InvestigationPanel
              incId={incId}
              onResolve={(e) => onResolve(incId, e)}
              status={inc.status}
            />
          )}

          {/* GENERAL COMMENTS — all incidents */}
          <CommentsPanel incId={incId} isReview={isReview} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// InvestigationPanel — shown only for REVIEW incidents
// ---------------------------------------------------------------------------
function InvestigationPanel({ incId, onResolve, status }) {
  const [notes, setNotes] = useState(() => getComments(`inv_${incId}`));
  const [draft, setDraft] = useState("");
  const [priority, setPriority] = useState("medium");

  function submitNote(e) {
    e.preventDefault();
    if (!draft.trim()) return;
    const note = {
      id: Date.now(),
      type: "investigation",
      author: "admin",
      text: draft.trim(),
      assignee: null,
      priority,
      timestamp: new Date().toISOString(),
    };
    addComment(`inv_${incId}`, note);
    setNotes(getComments(`inv_${incId}`));
    setDraft("");
  }

  return (
    <div style={{
      marginBottom: 16,
      border: "1px solid rgba(245,158,11,0.35)",
      borderRadius: "var(--radius)",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        background: "rgba(245,158,11,0.08)",
        borderBottom: "1px solid rgba(245,158,11,0.2)",
        padding: "10px 14px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 14 }}>🔍</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--amber)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Investigation Panel
          </span>
        </div>
        {status !== "RESOLVED" && (
          <button
            className="btn btn-sm"
            style={{ background: "var(--amber)", color: "#000", fontWeight: 600, fontSize: 11 }}
            onClick={onResolve}
          >
            ✓ Mark Resolved
          </button>
        )}
      </div>

      <div style={{ padding: 14 }}>
        {/* Meta row */}
        <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
          <div style={{ width: 140 }}>
            <div style={{ fontSize: 10, color: "var(--text2)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Priority</div>
            <select
              className="input"
              style={{ width: "100%", fontSize: 12 }}
              value={priority}
              onChange={e => setPriority(e.target.value)}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>

        {/* Existing investigation notes */}
        {notes.length > 0 && (
          <div style={{ marginBottom: 12, display: "flex", flexDirection: "column", gap: 8 }}>
            {notes.map(n => (
              <InvestigationNote key={n.id} note={n} />
            ))}
          </div>
        )}

        {/* New note form */}
        <form onSubmit={submitNote} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <textarea
            className="input"
            style={{ resize: "vertical", minHeight: 72, fontSize: 12, fontFamily: "inherit", lineHeight: 1.5 }}
            placeholder="Add investigatory note — findings, evidence, next steps…"
            value={draft}
            onChange={e => setDraft(e.target.value)}
          />
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="submit"
              className="btn btn-sm"
              style={{ background: "var(--amber)", color: "#000", fontWeight: 600, opacity: draft.trim() ? 1 : 0.45 }}
              disabled={!draft.trim()}
            >
              Add Investigation Note
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function InvestigationNote({ note }) {
  const priorityColors = { low: "var(--green)", medium: "var(--accent)", high: "var(--amber)", critical: "var(--red)" };
  return (
    <div style={{
      background: "rgba(245,158,11,0.05)",
      border: "1px solid rgba(245,158,11,0.15)",
      borderRadius: "var(--radius)",
      padding: "10px 12px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{
          width: 22, height: 22, borderRadius: "50%",
          background: "var(--amber)", color: "#000",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 10, fontWeight: 700, flexShrink: 0,
        }}>
          {note.author?.[0]?.toUpperCase() || "A"}
        </span>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text0)" }}>{note.author}</span>
        {note.assignee && (
          <span style={{ fontSize: 11, color: "var(--text2)" }}>→ <em>{note.assignee}</em></span>
        )}
        <span style={{
          marginLeft: "auto", fontSize: 10, fontWeight: 600,
          color: priorityColors[note.priority] || "var(--text2)",
          textTransform: "uppercase", letterSpacing: "0.05em",
        }}>
          {note.priority}
        </span>
        <span style={{ fontSize: 10, color: "var(--text2)" }}>{fmtTime(note.timestamp)}</span>
      </div>
      <div style={{ fontSize: 12, color: "var(--text1)", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{note.text}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CommentsPanel — shown for all incidents
// ---------------------------------------------------------------------------
function CommentsPanel({ incId, isReview }) {
  const [comments, setComments] = useState(() => getComments(`gen_${incId}`));
  const [draft, setDraft] = useState("");

  function submitComment(e) {
    e.preventDefault();
    if (!draft.trim()) return;
    const comment = {
      id: Date.now(),
      author: "admin",
      text: draft.trim(),
      timestamp: new Date().toISOString(),
    };
    addComment(`gen_${incId}`, comment);
    setComments(getComments(`gen_${incId}`));
    setDraft("");
  }

  return (
    <div style={{
      border: "1px solid var(--border2)",
      borderRadius: "var(--radius)",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        background: "var(--bg2)",
        borderBottom: "1px solid var(--border)",
        padding: "10px 14px",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <span style={{ fontSize: 13 }}>💬</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text0)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Comments
        </span>
        {comments.length > 0 && (
          <span style={{
            marginLeft: 4, background: "var(--accent)", color: "#fff",
            borderRadius: 10, fontSize: 10, fontWeight: 700,
            padding: "1px 6px",
          }}>
            {comments.length}
          </span>
        )}
      </div>

      <div style={{ padding: 14 }}>
        {/* Existing comments */}
        {comments.length === 0 ? (
          <div style={{ fontSize: 12, color: "var(--text2)", textAlign: "center", padding: "12px 0", marginBottom: 12 }}>
            No comments yet.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
            {comments.map(c => (
              <CommentBubble key={c.id} comment={c} />
            ))}
          </div>
        )}

        {/* New comment form */}
        <form onSubmit={submitComment} style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <textarea
            className="input"
            style={{ flex: 1, resize: "none", height: 60, fontSize: 12, fontFamily: "inherit", lineHeight: 1.5 }}
            placeholder="Add a comment…"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitComment(e);
            }}
          />
          <button
            type="submit"
            className="btn btn-sm"
            style={{ flexShrink: 0, fontWeight: 600, opacity: draft.trim() ? 1 : 0.45 }}
            disabled={!draft.trim()}
          >
            Post
          </button>
        </form>
        <div style={{ fontSize: 10, color: "var(--text2)", marginTop: 4 }}>⌘ + Enter to submit</div>
      </div>
    </div>
  );
}

function CommentBubble({ comment }) {
  return (
    <div style={{
      display: "flex", gap: 10, alignItems: "flex-start",
    }}>
      <div style={{
        width: 26, height: 26, borderRadius: "50%",
        background: "var(--accent)", color: "#fff",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 11, fontWeight: 700, flexShrink: 0, marginTop: 2,
      }}>
        {comment.author?.[0]?.toUpperCase() || "A"}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 3 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text0)" }}>{comment.author}</span>
          <span style={{ fontSize: 10, color: "var(--text2)" }}>{fmtTime(comment.timestamp)}</span>
        </div>
        <div style={{
          background: "var(--bg2)", borderRadius: "var(--radius)",
          padding: "8px 12px", fontSize: 12, color: "var(--text1)",
          lineHeight: 1.6, whiteSpace: "pre-wrap",
        }}>
          {comment.text}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------
function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 11, color: "var(--text2)", marginBottom: 6, fontWeight: 500,
      textTransform: "uppercase", letterSpacing: "0.05em",
    }}>
      {children}
    </div>
  );
}

function ScoreBar({ label, value }) {
  const color = value >= 0.75 ? "var(--red)" : value >= 0.55 ? "var(--amber)" : "var(--green)";
  return (
    <div style={{ textAlign: "right", minWidth: 80 }}>
      <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 4 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <div style={{ width: 48, height: 4, background: "var(--bg4)", borderRadius: 2, overflow: "hidden" }}>
          <div style={{ width: `${Math.round(value * 100)}%`, height: "100%", background: color, borderRadius: 2 }} />
        </div>
        <span style={{ fontSize: 12, color, fontFamily: "var(--mono)", fontWeight: 500 }}>
          {Math.round(value * 100)}%
        </span>
      </div>
    </div>
  );
}

function InfoCell({ label, value, highlight }) {
  return (
    <div style={{ background: "var(--bg2)", borderRadius: "var(--radius)", padding: "10px 12px" }}>
      <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ fontSize: 13, color: highlight ? "var(--red)" : "var(--text0)", fontWeight: 500 }}>{value}</div>
    </div>
  );
}
