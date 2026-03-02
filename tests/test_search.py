"""Tests for search.py FTS5 module and new Flask endpoints (Plan 18-01).

TDD RED: tests written first, implemented in search.py and app.py (Task 2).
"""
import importlib
import json
import sqlite3

import pytest

# ---------------------------------------------------------------------------
# FTS5 availability check — skip entire module if sqlite3 was compiled
# without FTS5 (rare on macOS/Linux, common on some stripped builds).
# ---------------------------------------------------------------------------

fts5_available = True
try:
    _con = sqlite3.connect(':memory:')
    _con.execute("CREATE VIRTUAL TABLE _t USING fts5(x)")
    _con.close()
except sqlite3.OperationalError:
    fts5_available = False

pytestmark = pytest.mark.skipif(not fts5_available, reason="SQLite FTS5 not available")


# ---------------------------------------------------------------------------
# search.py — init_db()
# ---------------------------------------------------------------------------

def test_init_db_creates_file(tmp_path):
    """init_db() creates output/search.db if it does not exist."""
    import search
    search.init_db(tmp_path)
    assert (tmp_path / 'search.db').exists()


def test_init_db_creates_fts5_table(tmp_path):
    """init_db() creates an FTS5 virtual table named 'articles'."""
    import search
    search.init_db(tmp_path)
    con = sqlite3.connect(str(tmp_path / 'search.db'))
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
    assert cur.fetchone() is not None
    con.close()


def test_init_db_idempotent(tmp_path):
    """Calling init_db() twice does not raise and leaves the DB intact."""
    import search
    search.init_db(tmp_path)
    search.init_db(tmp_path)  # must not raise
    assert (tmp_path / 'search.db').exists()


# ---------------------------------------------------------------------------
# search.py — index_stem()
# ---------------------------------------------------------------------------

def test_index_stem_inserts_regions(tmp_path):
    """index_stem() inserts all regions for a stem into the FTS5 table."""
    import search
    search.init_db(tmp_path)
    regions = [
        {'id': 'r0', 'type': 'headline', 'title': 'Berliner Nachrichten'},
        {'id': 'r1', 'type': 'article', 'title': 'Stadtrat beschliesst Bau'},
    ]
    search.index_stem(tmp_path, 'scan_001', regions)
    con = sqlite3.connect(str(tmp_path / 'search.db'))
    rows = con.execute('SELECT stem, region_id, type, title FROM articles').fetchall()
    con.close()
    assert len(rows) == 2
    stems = {r[0] for r in rows}
    assert stems == {'scan_001'}


def test_index_stem_is_idempotent(tmp_path):
    """Calling index_stem() twice for the same stem replaces rather than duplicates rows."""
    import search
    search.init_db(tmp_path)
    regions = [{'id': 'r0', 'type': 'headline', 'title': 'Original'}]
    search.index_stem(tmp_path, 'scan_001', regions)
    search.index_stem(tmp_path, 'scan_001', regions)  # second call
    con = sqlite3.connect(str(tmp_path / 'search.db'))
    rows = con.execute('SELECT stem FROM articles').fetchall()
    con.close()
    assert len(rows) == 1  # not duplicated


def test_index_stem_empty_regions(tmp_path):
    """index_stem() with an empty regions list removes all rows for that stem."""
    import search
    search.init_db(tmp_path)
    regions = [{'id': 'r0', 'type': 'headline', 'title': 'Will be removed'}]
    search.index_stem(tmp_path, 'scan_001', regions)
    search.index_stem(tmp_path, 'scan_001', [])
    con = sqlite3.connect(str(tmp_path / 'search.db'))
    rows = con.execute('SELECT stem FROM articles').fetchall()
    con.close()
    assert len(rows) == 0


# ---------------------------------------------------------------------------
# search.py — query()
# ---------------------------------------------------------------------------

def test_query_finds_match(tmp_path):
    """query() returns matching articles ranked by relevance."""
    import search
    search.init_db(tmp_path)
    search.index_stem(tmp_path, 'scan_001', [
        {'id': 'r0', 'type': 'headline', 'title': 'Berliner Nachrichten'},
    ])
    results = search.query(tmp_path, 'Berliner')
    assert len(results) == 1
    assert results[0]['stem'] == 'scan_001'
    assert results[0]['region_id'] == 'r0'
    assert results[0]['type'] == 'headline'
    assert results[0]['title'] == 'Berliner Nachrichten'


def test_query_no_match_returns_empty(tmp_path):
    """query() returns [] when no articles match the query."""
    import search
    search.init_db(tmp_path)
    search.index_stem(tmp_path, 'scan_001', [
        {'id': 'r0', 'type': 'article', 'title': 'Stadtrat'},
    ])
    results = search.query(tmp_path, 'Berliner')
    assert results == []


def test_query_empty_string_returns_empty(tmp_path):
    """query() with empty string returns [] without error."""
    import search
    search.init_db(tmp_path)
    results = search.query(tmp_path, '')
    assert results == []


def test_query_no_db_returns_empty(tmp_path):
    """query() returns [] gracefully when search.db does not exist."""
    import search
    results = search.query(tmp_path, 'anything')
    assert results == []


# ---------------------------------------------------------------------------
# app.py — GET /articles/<stem>
# ---------------------------------------------------------------------------

def test_get_articles_returns_regions(client, tmp_path, monkeypatch):
    """GET /articles/<stem> returns region list from segment JSON (200)."""
    monkeypatch.setitem(client.application.config, 'OUTPUT_DIR', str(tmp_path))
    seg_dir = tmp_path / 'segments'
    seg_dir.mkdir()
    segment = {
        'stem': 'scan_001',
        'provider': 'test',
        'model': 'test',
        'segmented_at': '2026-03-02T10:00:00+00:00',
        'regions': [
            {'id': 'r0', 'type': 'headline', 'title': 'Test Headline',
             'bounding_box': {'x': 0.1, 'y': 0.1, 'width': 0.8, 'height': 0.1}},
        ],
    }
    (seg_dir / 'scan_001.json').write_text(json.dumps(segment))
    resp = client.get('/articles/scan_001')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'regions' in data
    assert len(data['regions']) == 1
    assert data['regions'][0]['type'] == 'headline'


def test_get_articles_not_segmented_returns_404(client, tmp_path, monkeypatch):
    """GET /articles/<stem> returns 404 when segment JSON does not exist."""
    monkeypatch.setitem(client.application.config, 'OUTPUT_DIR', str(tmp_path))
    (tmp_path / 'segments').mkdir()
    resp = client.get('/articles/nosuchstem')
    assert resp.status_code == 404


def test_get_articles_path_traversal_returns_400(client):
    """GET /articles/<stem> with '..' in stem returns 400."""
    resp = client.get('/articles/..%2Fetc%2Fpasswd')
    assert resp.status_code in (400, 404)


# ---------------------------------------------------------------------------
# app.py — GET /search?q=
# ---------------------------------------------------------------------------

def test_search_endpoint_returns_matches(client, tmp_path, monkeypatch):
    """GET /search?q=text returns ranked matches from FTS5 DB."""
    import search as search_mod
    monkeypatch.setitem(client.application.config, 'OUTPUT_DIR', str(tmp_path))
    # Pre-populate DB
    search_mod.init_db(tmp_path)
    search_mod.index_stem(tmp_path, 'scan_001', [
        {'id': 'r0', 'type': 'headline', 'title': 'Berliner Nachrichten'},
    ])
    resp = client.get('/api/search?q=Berliner')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'results' in data
    assert len(data['results']) >= 1
    assert data['results'][0]['stem'] == 'scan_001'


def test_search_endpoint_empty_query(client, tmp_path, monkeypatch):
    """GET /api/search with no q param or empty q returns 200 with empty results."""
    monkeypatch.setitem(client.application.config, 'OUTPUT_DIR', str(tmp_path))
    resp = client.get('/api/search?q=')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['results'] == []


def test_search_endpoint_no_db(client, tmp_path, monkeypatch):
    """GET /api/search returns 200 with empty results when search.db does not exist."""
    monkeypatch.setitem(client.application.config, 'OUTPUT_DIR', str(tmp_path))
    resp = client.get('/api/search?q=anything')
    assert resp.status_code == 200
    assert resp.get_json()['results'] == []


# ---------------------------------------------------------------------------
# app.py — auto-index hook in segment_page()
# ---------------------------------------------------------------------------

def test_segment_page_auto_indexes(client, tmp_path, monkeypatch):
    """POST /segment/<stem> calls search.index_stem() after saving segment JSON."""
    import search as search_mod
    app_module = importlib.import_module('app')
    monkeypatch.setitem(client.application.config, 'OUTPUT_DIR', str(tmp_path))

    # Setup: provider returns one region
    mock_provider = __import__('unittest.mock', fromlist=['MagicMock']).MagicMock()
    mock_provider.segment.return_value = [
        {'id': 'r0', 'type': 'headline', 'title': 'Auto Index Test',
         'bounding_box': {'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 0.1}},
    ]
    monkeypatch.setattr(app_module, '_make_provider_from_settings', lambda s: mock_provider)

    # Create JPEG cache entry
    (tmp_path / 'jpegcache').mkdir()
    (tmp_path / 'jpegcache' / 'scan_001.jpg').write_bytes(b'FAKEJPEG')

    resp = client.post('/segment/scan_001')
    assert resp.status_code == 200

    # Verify search DB was updated
    results = search_mod.query(tmp_path, 'Auto Index')
    assert len(results) >= 1
    assert results[0]['stem'] == 'scan_001'
