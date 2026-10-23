import sqlite3, json, datetime, os
from backend.app.config import config

def get_conn():
    path = config.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True) if os.path.dirname(path) else None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS drafts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        auth0_sub TEXT NOT NULL,
        mode TEXT NOT NULL DEFAULT 'A',
        original TEXT NOT NULL,
        goal TEXT NOT NULL,
        rewrite TEXT,
        atoms_json TEXT,
        verdict TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        gmail_draft_id TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS threads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        auth0_sub TEXT NOT NULL,
        contact_id INTEGER,
        sender_email TEXT,
        subject TEXT,
        snippet TEXT,
        fetched_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        auth0_sub TEXT NOT NULL,
        name TEXT,
        email TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draft_id INTEGER,
        kind TEXT NOT NULL,
        payload_json TEXT,
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def now():
    return datetime.datetime.utcnow().isoformat() + "Z"

def log_event(draft_id, kind, payload):
    conn = get_conn()
    conn.execute("INSERT INTO events(draft_id, kind, payload_json, created_at) VALUES (?,?,?,?)",
                 (draft_id, kind, json.dumps(payload), now()))
    conn.commit()
    conn.close()
