"""
Shared file-cleanup utilities for all apps.
Files (and their DB records) older than TTL_HOURS are deleted on each index page load.
"""
import os
from datetime import datetime, timedelta
from db import get_db

TTL_HOURS = 1


def _cutoff():
    return (datetime.utcnow() - timedelta(hours=TTL_HOURS)).isoformat()


def purge_legal_uploads(upload_dir):
    """Delete legal uploaded documents older than TTL_HOURS."""
    cutoff = _cutoff()
    conn = get_db()
    expired = conn.execute(
        "SELECT id, filename FROM legal_documents WHERE created_at < ?", (cutoff,)
    ).fetchall()
    for row in expired:
        _rm(os.path.join(upload_dir, row["filename"]))
        conn.execute("DELETE FROM legal_analyses WHERE doc_id=?", (row["id"],))
        conn.execute("DELETE FROM legal_documents WHERE id=?", (row["id"],))
    # Also remove any orphaned files not tracked in the DB
    _purge_orphans(upload_dir, {r["filename"] for r in conn.execute(
        "SELECT filename FROM legal_documents").fetchall()})
    conn.commit()
    conn.close()


def purge_gen_files(gen_dir):
    """Delete gen-app generated PDFs older than TTL_HOURS."""
    cutoff = _cutoff()
    conn = get_db()
    expired = conn.execute(
        "SELECT id, out_file FROM gen_projects WHERE created_at < ?", (cutoff,)
    ).fetchall()
    for row in expired:
        _rm(os.path.join(gen_dir, row["out_file"]))
        conn.execute("DELETE FROM gen_projects WHERE id=?", (row["id"],))
    # Also remove orphaned files not tracked in the DB
    _purge_orphans(gen_dir, {r["out_file"] for r in conn.execute(
        "SELECT out_file FROM gen_projects").fetchall()})
    conn.commit()
    conn.close()


def purge_optimizer_files(gen_dir):
    """Delete optimizer-app generated TXT exports older than TTL_HOURS."""
    cutoff = _cutoff()
    conn = get_db()
    expired = conn.execute(
        "SELECT id FROM opt_projects WHERE created_at < ?", (cutoff,)
    ).fetchall()
    for row in expired:
        conn.execute("DELETE FROM opt_projects WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    _purge_orphans(gen_dir, set())


def purge_bulk_files(gen_dir):
    """Delete bulk-app generated CSV files older than TTL_HOURS."""
    cutoff = _cutoff()
    conn = get_db()
    expired_batches = conn.execute(
        "SELECT id FROM bulk_batches WHERE created_at < ?", (cutoff,)
    ).fetchall()
    for row in expired_batches:
        conn.execute("DELETE FROM bulk_books WHERE batch_id=?", (row["id"],))
        conn.execute("DELETE FROM bulk_batches WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    _purge_orphans(gen_dir, set())


def purge_finder_files(gen_dir):
    """Delete finder-app saved searches older than TTL_HOURS."""
    cutoff = _cutoff()
    conn = get_db()
    conn.execute("DELETE FROM finder_searches WHERE created_at < ?", (cutoff,))
    conn.commit()
    conn.close()
    _purge_orphans(gen_dir, set())


def _rm(path):
    """Silently remove a file if it exists."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _purge_orphans(directory, known_filenames):
    """Remove any files in directory that are not in known_filenames."""
    try:
        for fname in os.listdir(directory):
            if fname not in known_filenames:
                _rm(os.path.join(directory, fname))
    except OSError:
        pass
