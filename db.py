import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── LEGAL ──────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS legal_documents (
        id TEXT PRIMARY KEY, filename TEXT, original_name TEXT,
        file_type TEXT, status TEXT DEFAULT 'pending', created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS legal_analyses (
        id TEXT PRIMARY KEY, doc_id TEXT, overall_risk TEXT,
        summary TEXT, clauses TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS legal_settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS legal_reports (
        id TEXT PRIMARY KEY, content_id TEXT, reason TEXT,
        description TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, reviewed_at TEXT, admin_note TEXT)""")

    # ── GEN ────────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS gen_projects (
        id TEXT PRIMARY KEY, title TEXT, project_type TEXT,
        template_id TEXT, prompt TEXT, page_count INTEGER,
        paper_size TEXT, out_file TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS gen_settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS gen_reports (
        id TEXT PRIMARY KEY, content_id TEXT, reason TEXT,
        description TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, reviewed_at TEXT, admin_note TEXT)""")

    # ── OPTIMIZER ──────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS opt_projects (
        id TEXT PRIMARY KEY, genre TEXT, audience TEXT,
        rough_title TEXT, raw_keywords TEXT, result TEXT,
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS opt_settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS opt_reports (
        id TEXT PRIMARY KEY, content_id TEXT, reason TEXT,
        description TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, reviewed_at TEXT, admin_note TEXT)""")

    # ── BULK ───────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS bulk_batches (
        id TEXT PRIMARY KEY, name TEXT, niche TEXT, book_count INTEGER,
        status TEXT DEFAULT 'pending', out_file TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bulk_books (
        id TEXT PRIMARY KEY, batch_id TEXT, title TEXT, subtitle TEXT,
        description TEXT, keywords TEXT, primary_category TEXT,
        secondary_category TEXT, pages INTEGER, language TEXT,
        status TEXT DEFAULT 'draft', price_usd REAL, target_audience TEXT,
        unique_angle TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bulk_settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bulk_reports (
        id TEXT PRIMARY KEY, content_id TEXT, reason TEXT,
        description TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, reviewed_at TEXT, admin_note TEXT)""")

    # ── FINDER ─────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS finder_searches (
        id TEXT PRIMARY KEY, seed_topic TEXT, results TEXT,
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS finder_settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS finder_reports (
        id TEXT PRIMARY KEY, content_id TEXT, reason TEXT,
        description TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, reviewed_at TEXT, admin_note TEXT)""")

    conn.commit()
    conn.close()


def get_setting(table, key, default=""):
    conn = get_db()
    row = conn.execute(f"SELECT value FROM {table} WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(table, key, value):
    conn = get_db()
    conn.execute(f"INSERT OR REPLACE INTO {table} (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()
