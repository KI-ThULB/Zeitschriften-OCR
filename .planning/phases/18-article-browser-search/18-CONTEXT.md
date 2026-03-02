# Phase 18 Context: Article Browser and Full-Text Search

## Goal

Operators can browse identified articles for any page in a viewer sidebar and search across all
articles by title or content from the web interface.

---

## Data Model

Segment JSON files already exist at `output/segments/<stem>.json` with this structure:

```json
{
  "stem": "scan_001",
  "provider": "openai_compatible",
  "model": "llama3.2-vision",
  "segmented_at": "2026-03-02T10:00:00+00:00",
  "regions": [
    {
      "id": "r0",
      "type": "headline",
      "title": "Berliner Nachrichten",
      "bounding_box": { "x": 0.05, "y": 0.02, "width": 0.90, "height": 0.08 }
    }
  ]
}
```

`bounding_box` values are **normalized (0–1)** fractions of `jpeg_width` / `jpeg_height`.

---

## Architecture Decisions

### Full-Text Search: SQLite FTS5

- Built into Python's `sqlite3` stdlib — no new dependency
- Search DB at `output/search.db`
- Schema: one FTS5 virtual table `articles(stem, region_id, type, title, body)` — body is the title
  text for now (OCR text integration is future work)
- Separate `search.py` module for DB create/upsert/query — keeps app.py clean
- Auto-indexed: `segment_page()` in app.py calls `search.index_stem(output_dir, stem, regions)`
  after writing the segment JSON — no manual rebuild needed
- On server start, `main()` does NOT bulk-index existing files — FTS5 DB is built incrementally
  as operators run Segment. A one-time rebuild CLI command is out of scope for Phase 18.

### New Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /articles/<stem>` | GET | Returns article list for one stem (reads segment JSON) |
| `GET /search?q=...` | GET | FTS5 ranked search, returns list of matches |

Both endpoints return JSON. `GET /articles/<stem>` delegates to the existing segment JSON file so
no DB read is required for simple article listing.

`GET /search?q=...` returns an array of matches, ranked by FTS5 BM25 relevance:

```json
[
  { "stem": "scan_001", "region_id": "r0", "type": "headline", "title": "Berliner Nachrichten" },
  ...
]
```

Empty `q` returns `[]`. No pagination in Phase 18.

### Article Sidebar in Viewer

The viewer already has:
- `#sidebar` (220px, left) — file list rendered by `renderSidebar()`
- `#text-panel` (380px, right) — OCR word spans + inline edit

Decision: Add the article list **below the OCR word text in `#text-panel`**, separated by a `<hr>`
and a heading. This keeps the sidebar for file navigation and avoids a fourth layout column.

Structure inside `#text-panel` after words render:

```
[OCR words...]
─────────────────────
Articles (3)
  [article card: type • title]    ← click highlights region
  [article card: ...]
```

Article cards are `<div class="article-card">` elements injected after `renderWords()` calls
`loadArticles(stem)`. Clicking a card calls `highlightRegion(region)` which converts normalized
bounding_box coords to SVG pixel coords (same math as `showSegmentRegions()`).

`highlightRegion()` scrolls the image panel to make the region visible and draws a pulsing
highlight rect on `#overlay` using a separate `<rect id="article-highlight-rect">` distinct from
the word `<rect id="highlight-rect">`.

### Search UI on Upload Dashboard

A search bar is added to `templates/upload.html` — the operator's entry point. It sits above the
file queue (or in the header area), with a text input and a Search button. Submitting navigates to
`/search?q=...` (a new server-rendered or JS-rendered page).

Decision: `GET /search?q=...` returns JSON consumed by a **new `templates/search.html`** page.
The search page is served at `GET /search` (no `q` param → renders empty). Clicking a result
navigates to `/viewer/<stem>#<region_id>` — the viewer detects the hash on load and highlights
the named region.

### Region Highlight from Search Result (Deep Link)

When the viewer loads with a URL hash like `#r2`, after `loadFile()` and `loadSegments()` complete,
JS reads `location.hash`, finds the matching region in the loaded segment data, and calls
`highlightRegion()` on it. This satisfies success criterion 4 (clicking a search result opens the
viewer with the matched article's region highlighted).

---

## File Ownership

| File | Plan |
|------|------|
| `search.py` | 18-01 |
| `tests/test_search.py` | 18-01 |
| `app.py` | 18-01 (new endpoints + auto-index hook) |
| `templates/viewer.html` | 18-02 |
| `templates/upload.html` | 18-02 |
| `templates/search.html` | 18-02 (new) |

---

## Dependency Order

Plan 18-01 (backend) must complete before Plan 18-02 (frontend) — the frontend calls
`/articles/<stem>` and `/search?q=...` which are implemented in 18-01.

---

## Key Links

| From | To | Via |
|------|----|-----|
| `segment_page()` in app.py | `search.db` | `search.index_stem()` after JSON write |
| `GET /articles/<stem>` | `output/segments/<stem>.json` | direct file read |
| `GET /search?q=` | `search.db` FTS5 table | `search.query()` |
| viewer.html `loadArticles()` | `GET /articles/<stem>` | fetch in `loadFile()` |
| search.html result click | `/viewer/<stem>#<region_id>` | link href |
| viewer.html on load | `location.hash` | `highlightRegionById()` |

---

## Constraints from Prior Phases

- `showSegmentRegions()` uses `jpeg_width` / `jpeg_height` module-level vars populated by `loadFile()`
  — `highlightRegion()` must use the same vars (already available)
- `clearSegmentRegions()` removes `.segment-region` and `.segment-label` — article highlight rect
  must use a different class/id so it is not cleared by segment operations
- Atomic write pattern (tempfile.mkstemp + os.replace) used for settings.json applies to search.db
  initialization — use `sqlite3.connect()` with `check_same_thread=False`; DB file is only written
  from Flask request threads (not from worker threads)
- All new endpoints must follow the `if '/' in stem or '..' in stem` path traversal guard pattern

---

## Out of Scope (Phase 18)

- Bulk re-index of existing segment files on server start
- Pagination of search results
- OCR text body in FTS5 (only title indexed for now)
- Snippet/excerpt display in search results
