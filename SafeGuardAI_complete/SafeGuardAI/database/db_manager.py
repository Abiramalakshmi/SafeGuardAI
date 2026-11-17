import sqlite3
import hashlib
import json
import os
from datetime import datetime
from utils.config import DB_PATH


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT NOT NULL,
            violence_score   REAL NOT NULL,
            emotion_detected TEXT,
            toxicity_score   REAL,
            aggression_score REAL DEFAULT 0.0,
            transcript       TEXT,
            toxic_phrases    TEXT,
            video_source     TEXT,
            clip_path        TEXT,
            alert_level      TEXT NOT NULL,
            status           TEXT DEFAULT 'OPEN'
        )
    """)

    # Migrations for existing databases
    try:
        c.execute("ALTER TABLE incidents ADD COLUMN aggression_score REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE incidents ADD COLUMN clip_path TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            role      TEXT DEFAULT 'admin'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'Viewer',
            status      TEXT NOT NULL DEFAULT 'active',
            created_at  TEXT NOT NULL,
            last_active TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            user        TEXT NOT NULL,
            action      TEXT NOT NULL,
            target      TEXT,
            category    TEXT NOT NULL,
            ip          TEXT DEFAULT '127.0.0.1',
            details     TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    pw_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO admins (username, password, role) VALUES (?, ?, ?)",
              ("admin", pw_hash, "superadmin"))

    c.execute("""
        INSERT OR IGNORE INTO users (name, email, password, role, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("Administrator", "admin@safeguard.ai", pw_hash,
          "Admin", "active", datetime.now().isoformat()))

    defaults = {
        "violence_threshold": "0.65",
        "toxicity_threshold": "0.60",
        "alert_sound":        "true",
        "visual_weight":      "0.50",
        "audio_weight":       "0.50",
        "frame_sample_rate":  "5",
        "whisper_model":      "base",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


# ── Incidents ─────────────────────────────────────────────
def insert_incident(violence_score, emotion_detected, toxicity_score,
                    transcript, toxic_phrases, video_source, alert_level,
                    aggression_score=0.0, clip_path=None):
    conn = get_connection()
    c    = conn.cursor()
    if isinstance(toxic_phrases, list):
        phrases_str = json.dumps(toxic_phrases)
    else:
        phrases_str = json.dumps([toxic_phrases] if toxic_phrases else [])
    c.execute("""
        INSERT INTO incidents
          (timestamp, violence_score, emotion_detected, toxicity_score,
           aggression_score, transcript, toxic_phrases, video_source,
           clip_path, alert_level, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
    """, (
        datetime.now().isoformat(),
        round(float(violence_score),   4),
        emotion_detected,
        round(float(toxicity_score),   4),
        round(float(aggression_score), 4),
        transcript or "",
        phrases_str,
        video_source,
        clip_path,
        alert_level,
    ))
    incident_id = c.lastrowid
    conn.commit()
    conn.close()
    return incident_id


def _parse_row(row: dict) -> dict:
    phrases = row.get("toxic_phrases", "")
    if phrases:
        try:
            parsed = json.loads(phrases)
            row["toxic_phrases"] = parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            row["toxic_phrases"] = [p.strip() for p in phrases.split(",") if p.strip()]
    else:
        row["toxic_phrases"] = []
    if "aggression_score" not in row or row["aggression_score"] is None:
        row["aggression_score"] = 0.0
    return row


def get_all_incidents(limit=200, status_filter=None, level_filter=None):
    conn = get_connection()
    c    = conn.cursor()
    query      = "SELECT * FROM incidents"
    params     = []
    conditions = []
    if status_filter:
        conditions.append("status = ?");      params.append(status_filter)
    if level_filter:
        conditions.append("alert_level = ?"); params.append(level_filter)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY incident_id DESC LIMIT ?"
    params.append(limit)
    rows = c.execute(query, params).fetchall()
    conn.close()
    return [_parse_row(dict(r)) for r in rows]


def get_incident_by_id(incident_id):
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
    ).fetchone()
    conn.close()
    return _parse_row(dict(row)) if row else None


def resolve_incident(incident_id):
    conn = get_connection()
    conn.execute("UPDATE incidents SET status = 'RESOLVED' WHERE incident_id = ?",
                 (incident_id,))
    conn.commit()
    conn.close()


def clear_all_incidents():
    conn = get_connection()
    conn.execute("DELETE FROM incidents")
    conn.commit()
    conn.close()


def get_stats():
    conn     = get_connection()
    c        = conn.cursor()
    total    = c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    unsafe   = c.execute("SELECT COUNT(*) FROM incidents WHERE alert_level='UNSAFE'").fetchone()[0]
    review   = c.execute("SELECT COUNT(*) FROM incidents WHERE alert_level='REVIEW'").fetchone()[0]
    safe     = c.execute("SELECT COUNT(*) FROM incidents WHERE alert_level='SAFE'").fetchone()[0]
    resolved = c.execute("SELECT COUNT(*) FROM incidents WHERE status='RESOLVED'").fetchone()[0]
    conn.close()
    return {"total": total, "unsafe": unsafe, "review": review,
            "safe": safe, "resolved": resolved}


def get_recent_incidents(n=10):
    return get_all_incidents(limit=n)


# ── Users ─────────────────────────────────────────────────
def get_all_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, name, email, role, status, created_at, last_active"
        " FROM users ORDER BY user_id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_by_id(user_id):
    conn = get_connection()
    row  = conn.execute(
        "SELECT user_id, name, email, role, status, created_at, last_active"
        " FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(name, email, password, role):
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    now     = datetime.now().isoformat()
    conn    = get_connection()
    c       = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (name, email, password, role, status, created_at)
            VALUES (?, ?, ?, ?, 'active', ?)
        """, (name, email, pw_hash, role, now))
        user_id = c.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Email '{email}' already exists")
    conn.close()
    return {"user_id": user_id, "name": name, "email": email,
            "role": role, "status": "active", "created_at": now}


def update_user(user_id, name, email, role):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET name=?, email=?, role=? WHERE user_id=?",
            (name, email, role, user_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Email '{email}' already in use")
    conn.close()
    return get_user_by_id(user_id)


def set_user_status(user_id, status):
    conn = get_connection()
    conn.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
    conn.commit()
    conn.close()


def reset_user_password(user_id, new_password):
    pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
    conn    = get_connection()
    conn.execute("UPDATE users SET password=? WHERE user_id=?", (pw_hash, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# ── Audit Logs ────────────────────────────────────────────
def log_action(user, action, target, category, ip="127.0.0.1", details=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO audit_logs (timestamp, user, action, target, category, ip, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), user, action, target, category, ip, details))
    conn.commit()
    conn.close()


def get_audit_logs(limit=200, category=None, user=None):
    conn       = get_connection()
    query      = "SELECT * FROM audit_logs"
    params     = []
    conditions = []
    if category:
        conditions.append("category = ?"); params.append(category)
    if user:
        conditions.append("user = ?");     params.append(user)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY log_id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_audit_logs():
    conn = get_connection()
    conn.execute("DELETE FROM audit_logs")
    conn.commit()
    conn.close()


# ── Admins (legacy) ───────────────────────────────────────
def verify_admin(username, password):
    username = username.strip()
    password = password.strip()
    pw_hash  = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM admins WHERE username=? AND password=?",
        (username, pw_hash)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Settings ──────────────────────────────────────────────
def get_setting(key, default=None):
    conn = get_connection()
    row  = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                 (key, str(value)))
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}
