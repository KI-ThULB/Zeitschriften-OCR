"""search.py — SQLite FTS5 full-text search index for article regions.

DB location: output/search.db
Table: articles (FTS5 virtual table)
Columns: stem, region_id, type, title

init_db(output_dir)                   — create DB and table if not present (idempotent)
index_stem(output_dir, stem, regions) — delete+insert all rows for stem
query(output_dir, q)                  — FTS5 ranked search, returns list of dicts
"""
import sqlite3
from pathlib import Path


def _db_path(output_dir: Path) -> Path:
    return Path(output_dir) / 'search.db'


def init_db(output_dir: Path) -> None:
    """Create output/search.db and the FTS5 articles table if they do not exist."""
    db = _db_path(output_dir)
    con = sqlite3.connect(str(db))
    try:
        con.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS articles "
            "USING fts5(stem UNINDEXED, region_id UNINDEXED, type UNINDEXED, title)"
        )
        con.commit()
    finally:
        con.close()


def index_stem(output_dir: Path, stem: str, regions: list) -> None:
    """Upsert all regions for a stem into the FTS5 table.

    Deletes all existing rows for the stem first (idempotent replace).
    regions is a list of dicts with keys: id, type, title.
    """
    db = _db_path(output_dir)
    con = sqlite3.connect(str(db))
    try:
        con.execute("DELETE FROM articles WHERE stem = ?", (stem,))
        con.executemany(
            "INSERT INTO articles(stem, region_id, type, title) VALUES (?, ?, ?, ?)",
            [(stem, r['id'], r.get('type', ''), r.get('title', '')) for r in regions],
        )
        con.commit()
    finally:
        con.close()


def query(output_dir: Path, q: str) -> list:
    """Search the FTS5 index for q. Returns [] on empty q or missing DB.

    Returns list of {stem, region_id, type, title} dicts, ranked by BM25.
    """
    if not q or not q.strip():
        return []
    db = _db_path(output_dir)
    if not db.exists():
        return []
    try:
        con = sqlite3.connect(str(db))
        try:
            cur = con.execute(
                "SELECT stem, region_id, type, title "
                "FROM articles "
                "WHERE articles MATCH ? "
                "ORDER BY rank",
                (q,),
            )
            rows = cur.fetchall()
        finally:
            con.close()
    except sqlite3.OperationalError:
        # Table does not exist yet or malformed query
        return []
    return [
        {'stem': r[0], 'region_id': r[1], 'type': r[2], 'title': r[3]}
        for r in rows
    ]
