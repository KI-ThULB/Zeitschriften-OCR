# Phase 9: Flask Foundation and Job State - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

A bootable `app.py` with background OCR threading, SSE progress stream, and per-file error isolation — no UI, just the server plumbing verified against real TIFFs. Upload, run, and stream endpoints only. Viewer UI is Phase 11, upload UI is Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Job State Model
- In-memory module-level dict — no database, no persistence across restarts
- States: `pending → running → done / error`
- Job record fields: `filename`, `state`, `word_count`, `elapsed_time`, `error_msg`
- Job list resets on each new POST /run call — clean slate per run

### SSE Event Structure
- Named events with JSON data: `event: file_done\ndata: {...}`
- Per-file payload: `filename`, `state`, `word_count`, `elapsed_time`, `error_msg`
- Final `event: run_complete` event emitted when all files finish
- No `file_started` events — only emit on completion
- Stream closes after `run_complete`; client reconnects on next /run POST

### Upload & Staging
- Uploaded TIFFs staged in `uploads/` subfolder inside the output directory
- POST /upload accepts multiple files per request
- Skip check: `alto/<stem>.xml` already exists in output dir (mirrors CLI skip-if-exists)
- Staged TIFFs kept after OCR completes — needed by Phase 10's `/image/<stem>` endpoint

### Concurrency Model
- One OCR run at a time — POST /run returns 409 if a run is already in progress
- Background OCR thread calls `pipeline.run_batch()` directly — no OCR logic duplication in app.py
- Flask dev server with `threaded=True` — no Gunicorn/gevent needed for local operator use
- GET /stream only active during a run; client opens stream after POSTing /run

### Claude's Discretion
- Thread safety details for the in-memory job dict (threading.Lock, etc.)
- Exact JSON response shapes for /upload and /run endpoints
- Error response format for 409 and validation failures

</decisions>

<specifics>
## Specific Ideas

- Reuse `pipeline.run_batch()` from the background thread — the thread wraps it and feeds SSE events from the returned results
- Phase 10's `/image/<stem>` depends on TIFFs remaining in `uploads/` — do not delete after OCR

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-flask-foundation-and-job-state*
*Context gathered: 2026-02-27*
