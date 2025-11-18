"""
Database module for LinkedIn cleanup project.
Provides SQLite helper functions for connection tracking.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from linkedin_cleanup import config


@contextmanager
def _get_db():
    """Get database connection with proper cleanup."""
    db_path = Path(config.PROGRESS_FILE)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    try:
        _init_db(conn)
        yield conn
    finally:
        conn.close()


def _init_db(conn: sqlite3.Connection):
    """Initialize database schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            message TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON connections(status)")
    conn.commit()


def get_pending_urls() -> List[str]:
    """Get all URLs with status='pending' or NULL."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT url FROM connections WHERE status IS NULL OR status = 'pending'"
        ).fetchall()
        return [row['url'] for row in rows]


def update_connection_status(url: str, status: str, message: Optional[str] = None, timestamp: Optional[str] = None):
    """Update connection status in database."""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    with _get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO connections (url, status, message, timestamp)
            VALUES (?, ?, ?, ?)
        """, (url, status, message or '', timestamp))
        conn.commit()


def get_all_connections() -> List[Dict]:
    """Get all connections for summary stats."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT url, status, message, timestamp FROM connections"
        ).fetchall()
        return [
            {
                'url': row['url'],
                'status': row['status'],
                'message': row['message'],
                'timestamp': row['timestamp']
            }
            for row in rows
        ]


def get_connection_status(url: str) -> Optional[str]:
    """Get status for a specific URL."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT status FROM connections WHERE url = ?",
            (url,)
        ).fetchone()
        return row['status'] if row else None

