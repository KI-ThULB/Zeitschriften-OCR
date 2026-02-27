# Phase 9: Flask Foundation and Job State - Research

**Researched:** 2026-02-27
**Domain:** Flask 3.x, Server-Sent Events, threading, file upload, in-memory job state
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Job State Model**
- In-memory module-level dict — no database, no persistence across restarts
- States: `pending → running → done / error`
- Job record fields: `filename`, `state`, `word_count`, `elapsed_time`, `error_msg`
- Job list resets on each new POST /run call — clean slate per run

**SSE Event Structure**
- Named events with JSON data: `event: file_done\ndata: {...}`
- Per-file payload: `filename`, `state`, `word_count`, `elapsed_time`, `error_msg`
- Final `event: run_complete` event emitted when all files finish
- No `file_started` events — only emit on completion
- Stream closes after `run_complete`; client reconnects on next /run POST

**Upload & Staging**
- Uploaded TIFFs staged in `uploads/` subfolder inside the output directory
- POST /upload accepts multiple files per request
- Skip check: `alto/<stem>.xml` already exists in output dir (mirrors CLI skip-if-exists)
- Staged TIFFs kept after OCR completes — needed by Phase 10's `/image/<stem>` endpoint

**Concurrency Model**
- One OCR run at a time — POST /run returns 409 if a run is already in progress
- Background OCR thread calls `pipeline.run_batch()` directly — no OCR logic duplication in app.py
- Flask dev server with `threaded=True` — no Gunicorn/gevent needed for local operator use
- GET /stream only active during a run; client opens stream after POSTing /run

### Claude's Discretion
- Thread safety details for the in-memory job dict (threading.Lock, etc.)
- Exact JSON response shapes for /upload and /run endpoints
- Error response format for 409 and validation failures

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROC-03 | Already-processed TIFFs in the queue are skipped automatically (same skip logic as CLI) | Skip check via `alto/<stem>.xml` existence mirrors pipeline.run_batch() force=False logic; upload endpoint must normalize stems consistently with pipeline path conventions |
| PROC-04 | Processing errors per file are shown in the UI without stopping the batch | Per-file error isolation already present in pipeline.run_batch() error_list; SSE `event: file_done` carries `error_msg` field; remaining files continue after error |
</phase_requirements>

---

## Summary

Phase 9 builds `app.py`: a Flask 3.1 server with three endpoints (`POST /upload`, `POST /run`, `GET /stream`), in-memory job state protected by `threading.Lock`, and SSE streaming via `queue.Queue`. No UI is built in this phase. The goal is verified, testable server plumbing with real TIFFs.

The core threading model is: Flask runs with `threaded=True` (default in Flask 3.x dev server). POST /run starts a `threading.Thread` that calls `pipeline.run_batch()` in the background. That thread communicates completion events to the SSE stream generator via a module-level `queue.Queue`. The SSE route generator blocks on `queue.get(timeout=30)` and yields each event as it arrives.

The critical architectural decision flagged in STATE.md is that `pipeline.run_batch()` internally uses `ProcessPoolExecutor`. Calling it from a `threading.Thread` is safe on macOS (spawn context does not inherit thread state), but the existing `run_batch()` function accumulates all results and returns them as a batch — it does not yield per-file events progressively. The CONTEXT.md states files should be processed one at a time with SSE events posted per file. The recommended implementation pattern is to call `process_tiff()` directly in a sequential loop from the background thread (one file at a time), posting to the SSE queue after each completion. This matches "wraps pipeline functions" while producing genuine progressive SSE. The planner must decide whether to call `process_tiff()` in a loop OR call `run_batch()` one-file-at-a-time (workers=1, one-element list per call).

**Primary recommendation:** Use Flask 3.1 with `threaded=True`, `queue.Queue` for SSE, `threading.Lock` for job state, `werkzeug.utils.secure_filename` for upload sanitization, and call `process_tiff()` directly in a background thread loop to achieve progressive per-file SSE events.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.3 (installed) | HTTP server, routing, Response | Official WSGI framework; `threaded=True` default in dev server |
| Werkzeug | 3.1.6 (installed) | `secure_filename`, `FileStorage` | Flask's WSGI toolkit; `secure_filename` prevents path traversal |
| Python `queue` | stdlib | Thread-safe queue for SSE events | Built-in; `Queue.get(timeout=N)` blocks then yields; no extra deps |
| Python `threading` | stdlib | `Thread`, `Lock`, `Event` for job state | Built-in; `Lock` protects shared dict; `Thread` for background OCR |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 (installed) | Test framework | All unit/integration tests |
| pytest-flask | 1.3.0 (installed) | Flask `app` and `client` fixtures | Reduces test boilerplate for Flask apps |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `queue.Queue` for SSE | Flask-SSE (Redis-backed) | Flask-SSE requires Redis, adds infrastructure; queue is zero-dep |
| `threading.Thread` | Celery, RQ | Task queue systems add Redis/broker; overkill for single-operator local tool |
| `threading.Lock` | No lock | Race condition on job state dict between upload thread and SSE stream reader |

**Installation:**
```bash
pip install flask werkzeug pytest pytest-flask
```

Note: Flask and Werkzeug are already installed in the environment (Flask 3.1.3, Werkzeug 3.1.6). Add both to `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure
```
app.py               # Flask application — all routes and state in one file (mirrors pipeline.py convention)
uploads/             # Created at runtime inside output_dir — staged TIFFs
output/
├── alto/            # Existing pipeline output — skip check uses this
├── uploads/         # Staged TIFFs (kept after OCR for Phase 10)
└── ...
```

`app.py` follows the same single-file convention as `pipeline.py`. No blueprints, no packages.

### Pattern 1: Module-Level Job State with Lock

**What:** A module-level dict stores per-file job records. A `threading.Lock` serializes all reads and writes. The SSE queue is a separate module-level `queue.Queue` reset at each run start.

**When to use:** Single-process, single-run-at-a-time server with no persistence requirement.

```python
# Source: threading stdlib docs + Flask threading guide
import threading
import queue

# --- Module-level state ---
_job_lock = threading.Lock()
_jobs: dict[str, dict] = {}       # stem → {filename, state, word_count, elapsed_time, error_msg}
_sse_queue: queue.Queue | None = None  # None when no run active
_run_active = threading.Event()    # set while a run is in progress

def _reset_run(stems: list[str]) -> None:
    """Reset job state for a new run. Called under _job_lock."""
    global _sse_queue
    _jobs.clear()
    for stem in stems:
        _jobs[stem] = {'filename': stem + '.tif', 'state': 'pending',
                       'word_count': None, 'elapsed_time': None, 'error_msg': None}
    _sse_queue = queue.Queue()
```

### Pattern 2: SSE Response Generator with Queue and Timeout Keepalive

**What:** The `/stream` route returns a streaming `Response` with `text/event-stream` MIME type. A generator function blocks on `queue.Queue.get(timeout=30)` and yields formatted SSE events. The 30-second timeout keepalive (comment line) prevents browser/proxy connection drops during long OCR runs.

**When to use:** Long-running background jobs where clients need progress without polling.

```python
# Source: Max Halford Flask SSE no-deps pattern (https://maxhalford.github.io/blog/flask-sse-no-deps/)
#         Flask streaming docs (https://flask.palletsprojects.com/en/stable/patterns/streaming/)
import json
from flask import Response, stream_with_context

def _format_sse(event: str, data: dict) -> str:
    """Format a named SSE event with JSON payload per the SSE spec."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

@app.get('/stream')
def stream():
    def generate():
        local_q = _sse_queue  # capture reference at stream-open time
        if local_q is None:
            return  # no active run — close immediately
        while True:
            try:
                msg = local_q.get(timeout=30)
                yield msg
                if msg.startswith('event: run_complete'):
                    break  # run done — generator exits, stream closes
            except queue.Empty:
                yield ': keepalive\n\n'  # SSE comment — prevents proxy timeout

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
```

**Critical header:** `X-Accel-Buffering: no` disables Nginx buffering if ever proxied. `Cache-Control: no-cache` is required by the SSE spec.

### Pattern 3: Background Thread Calling process_tiff() Directly

**What:** The background thread calls `pipeline.process_tiff()` in a sequential loop (not `run_batch()`), posts SSE events after each file, and closes the SSE queue with `run_complete`.

**Why not run_batch():** `run_batch()` uses `ProcessPoolExecutor` internally and accumulates all results before returning. There is no hook to post SSE events as each file completes within `run_batch()`. For progressive SSE ("events arrive while OCR is running"), the background thread must be the one iterating per-file completion.

**Pattern:**
```python
# Source: pipeline.py analysis — process_tiff() API understood from source
import pipeline
import threading
import time

def _ocr_worker(tiff_paths: list[Path], output_dir: Path, lang: str,
                psm: int, padding: int) -> None:
    """Background thread: run OCR sequentially, post SSE events per file."""
    try:
        for tiff_path in tiff_paths:
            stem = tiff_path.stem
            t0 = time.monotonic()
            error_msg = None
            word_count = None

            # Skip check (PROC-03): mirrors pipeline skip-if-exists logic
            alto_path = output_dir / 'alto' / (stem + '.xml')
            if alto_path.exists():
                state = 'skipped'
                elapsed = 0.0
            else:
                try:
                    pipeline.process_tiff(
                        tiff_path, output_dir,
                        lang=lang, psm=psm, padding=padding,
                        no_crop=False, adaptive_threshold=False
                    )
                    elapsed = time.monotonic() - t0
                    # Read word count from written ALTO (pipeline already wrote it)
                    from lxml import etree
                    import pipeline as p
                    root = etree.parse(str(alto_path)).getroot()
                    word_count = p.count_words(root, p.ALTO21_NS)
                    state = 'done'
                except Exception as e:
                    elapsed = time.monotonic() - t0
                    error_msg = str(e)
                    state = 'error'

            # Update job state
            with _job_lock:
                _jobs[stem].update({
                    'state': state,
                    'word_count': word_count,
                    'elapsed_time': round(elapsed, 2),
                    'error_msg': error_msg,
                })

            # Post SSE event
            payload = _jobs[stem].copy()
            _sse_queue.put(_format_sse('file_done', payload))

        # Run complete
        _sse_queue.put(_format_sse('run_complete', {'total': len(tiff_paths)}))
    finally:
        _run_active.clear()
```

### Pattern 4: POST /upload — Multiple Files, Skip Check, Stage to uploads/

**What:** Accept multiple TIFF files per request, sanitize filenames with `secure_filename`, save to `uploads/` subfolder, check if alto already exists (skip if so), return per-file status.

```python
# Source: Flask file upload docs (https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
from werkzeug.utils import secure_filename

@app.post('/upload')
def upload():
    files = request.files.getlist('files')  # multi-file field named "files"
    if not files:
        return {'error': 'no files provided'}, 400

    results = []
    upload_dir = Path(app.config['OUTPUT_DIR']) / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        if not f.filename:
            continue
        filename = secure_filename(f.filename)
        if not filename.lower().endswith(('.tif', '.tiff')):
            results.append({'filename': filename, 'status': 'rejected', 'reason': 'not a TIFF'})
            continue

        dest = upload_dir / filename
        f.save(str(dest))

        stem = Path(filename).stem
        alto_path = Path(app.config['OUTPUT_DIR']) / 'alto' / (stem + '.xml')
        already_done = alto_path.exists()

        with _job_lock:
            _jobs[stem] = {
                'filename': filename,
                'state': 'done' if already_done else 'pending',
                'word_count': None, 'elapsed_time': None, 'error_msg': None,
            }
        results.append({'filename': filename, 'status': 'staged',
                        'already_processed': already_done})

    return {'files': results}, 200
```

### Pattern 5: POST /run — 409 Guard, Background Thread Launch

**What:** Check if a run is in progress (return 409), reset job state, start background thread, return 202 immediately.

```python
@app.post('/run')
def run():
    if _run_active.is_set():
        return {'error': 'a run is already in progress'}, 409

    with _job_lock:
        pending = [stem for stem, job in _jobs.items()
                   if job['state'] == 'pending']

    if not pending:
        return {'error': 'no pending files'}, 400

    _run_active.set()
    upload_dir = Path(app.config['OUTPUT_DIR']) / 'uploads'
    tiff_paths = [upload_dir / (stem + '.tif') for stem in pending]

    # Reset SSE queue for new run
    global _sse_queue
    with _job_lock:
        _sse_queue = queue.Queue()

    t = threading.Thread(
        target=_ocr_worker,
        args=(tiff_paths, Path(app.config['OUTPUT_DIR']),
              app.config.get('LANG', 'deu'),
              app.config.get('PSM', 1),
              app.config.get('PADDING', 50)),
        daemon=True,
    )
    t.start()
    return {'status': 'started', 'files': pending}, 202
```

**daemon=True** — ensures the background thread does not prevent process exit if Flask is killed.

### Anti-Patterns to Avoid

- **Accessing `request` inside the SSE generator after yield:** The request context is torn down before the generator resumes. Capture any needed request data BEFORE returning the Response. Use `stream_with_context()` if you must access request in the generator.
- **Not passing `app._get_current_object()` to the background thread:** `current_app` is a thread-local proxy. If the background thread needs the Flask app object (e.g., to access `app.config`), capture the real object with `app._get_current_object()` before thread launch and pass it as a parameter.
- **Forgetting `_run_active.clear()` in the finally block:** If OCR raises an uncaught exception, `_run_active` stays set and POST /run returns 409 forever. Always clear in `finally`.
- **Not setting `Cache-Control: no-cache` on SSE response:** Required by SSE spec; browsers may cache the stream without it.
- **Using `sys.exit()` in `process_tiff()`:** Already fixed in Phase 1 (`process_tiff()` must `raise`, not `sys.exit()`). This property is critical for the web worker — a `sys.exit()` would kill the entire Flask process.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Filename sanitization | String replace / regex on filename | `werkzeug.utils.secure_filename` | Path traversal edge cases (../../../etc, null bytes, Windows device names) are subtle; `secure_filename` handles all of them |
| Thread-safe queue | Manual list + Lock | `queue.Queue` | Already thread-safe; `get(timeout=N)` handles blocking + timeout atomically; `put_nowait` raises `Full` on overflow |
| SSE keepalive | Custom timer thread | `queue.get(timeout=30)` + `': keepalive\n\n'` yield | Zero extra threads; SSE comment lines (`: ...`) are spec-compliant and ignored by browsers |
| 409 run guard | Boolean flag | `threading.Event` | `Event.is_set()` / `Event.set()` / `Event.clear()` are atomic; boolean flags are not |

**Key insight:** The stdlib threading primitives (`Lock`, `Event`, `Queue`) are purpose-built for this pattern. Custom synchronization in Python is harder to get right than it appears.

---

## Common Pitfalls

### Pitfall 1: SSE Generator Blocks Forever After run_complete

**What goes wrong:** The generator loops on `queue.get()` but never breaks after `run_complete`. The browser connection stays open, and on the next run the client never sees a new stream because it's still attached to the old one.
**Why it happens:** Missing `break` or `return` in the generator after detecting `run_complete`.
**How to avoid:** After yielding `run_complete`, immediately break from the generator loop. The `Response` closes naturally when the generator is exhausted.
**Warning signs:** `/stream` endpoint never returns 200; browser EventSource stays connected across multiple runs.

### Pitfall 2: stem Normalization Inconsistency

**What goes wrong:** `/upload` stores file as `secure_filename("Scan 001.TIF")` → `"Scan_001.TIF"`. The skip check looks for `alto/Scan_001.xml`, but pipeline writes `alto/scan_001.xml` (lowercase stem). Skip check always misses.
**Why it happens:** `secure_filename` does not lowercase. `Path.stem` preserves case. Pipeline uses the TIFF's original stem.
**How to avoid:** Normalize stems to lowercase consistently in upload, skip check, and job dict keys. Use `filename.lower()` after `secure_filename`, or use `Path(secure_filename(f.filename)).stem.lower()` everywhere.
**Warning signs:** PROC-03 test fails — already-processed TIFFs are not skipped.

### Pitfall 3: Background Thread Loses app.config Access

**What goes wrong:** Background thread accesses `app.config['OUTPUT_DIR']` directly. This works locally but can raise `RuntimeError: Working outside of application context` in some Flask configurations.
**Why it happens:** `current_app` is a thread-local proxy — valid only in request-handling threads.
**How to avoid:** Capture config values as plain Python objects before launching the thread and pass them as arguments. Do NOT pass `current_app` or access it inside the thread. Alternatively, pass `app._get_current_object()` to the thread and access `.config` on it directly.
**Warning signs:** `RuntimeError: Working outside of application context` in background thread logs.

### Pitfall 4: ProcessPoolExecutor macOS Spawn Interaction

**What goes wrong:** `pipeline.run_batch()` internally creates a `ProcessPoolExecutor`. On macOS (Python 3.8+, default spawn context), calling `run_batch()` from a Flask background thread that itself is spawned by a threaded Flask server can trigger `OSError: [Errno 35] Resource temporarily unavailable` or hang if the spawn mechanism tries to fork a process from a multithreaded parent.
**Why it happens:** macOS's spawn-based multiprocessing starts fresh Python interpreter instances; combined with certain Flask thread states this can produce resource contention.
**How to avoid:** Call `process_tiff()` directly in a sequential loop from the background thread — avoid `run_batch()` / `ProcessPoolExecutor` entirely in the web worker. Sequential processing is acceptable for the local single-operator tool.
**Warning signs:** Background thread hangs; no SSE events arrive; `OSError` in stderr.

### Pitfall 5: Uploaded .TIF vs .tiff Suffix Detection

**What goes wrong:** Skip check uses `alto/<stem>.xml` where stem comes from `secure_filename`. Filename `scan_001.TIFF` becomes `scan_001.TIFF`; stem is `scan_001`. Pipeline already wrote `alto/scan_001.xml`. Skip check works. But suffix check `filename.lower().endswith('.tif')` fails for `.tiff`. Always check both suffixes.
**How to avoid:** `Path(filename).suffix.lower() in ('.tif', '.tiff')` — matches both, case-insensitively.

### Pitfall 6: SSE Response Buffering by Flask Dev Server

**What goes wrong:** Events are generated but don't reach the browser until the buffer flushes (often 4KB or full response end).
**Why it happens:** Werkzeug's dev server buffers responses by default.
**How to avoid:** Set `X-Accel-Buffering: no` header. Ensure the SSE generator yields immediately. Test with `curl -N http://localhost:5000/stream` (curl respects streaming) before browser testing.

---

## Code Examples

### SSE Event Format (SSE Spec Compliant)
```python
# Source: SSE spec (https://html.spec.whatwg.org/multipage/server-sent-events.html)
# Named event with JSON payload
def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

# SSE comment for keepalive (ignored by EventSource API)
KEEPALIVE = ': keepalive\n\n'

# Examples:
_format_sse('file_done', {
    'filename': 'scan_001.tif',
    'state': 'done',
    'word_count': 312,
    'elapsed_time': 8.4,
    'error_msg': None,
})
# → 'event: file_done\ndata: {"filename": "scan_001.tif", "state": "done", "word_count": 312, "elapsed_time": 8.4, "error_msg": null}\n\n'

_format_sse('run_complete', {'total': 3, 'errors': 0, 'skipped': 1})
# → 'event: run_complete\ndata: {"total": 3, "errors": 0, "skipped": 1}\n\n'
```

### Multiple File Upload via request.files.getlist()
```python
# Source: Flask file upload docs (https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
from werkzeug.utils import secure_filename

files = request.files.getlist('files')  # HTML: <input type="file" name="files" multiple>
for f in files:
    if f.filename == '':
        continue
    filename = secure_filename(f.filename)
    f.save(upload_dir / filename)
```

### Flask App Startup with threaded=True
```python
# Source: Flask docs — threaded=True is default in Flask 3.x dev server
# Explicit is clearer for this use case
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

### pytest-flask App Fixture
```python
# Source: pytest-flask docs (https://pytest-flask.readthedocs.io/)
# tests/conftest.py
import pytest
from app import create_app  # or: from app import app

@pytest.fixture()
def app():
    app.config['TESTING'] = True
    app.config['OUTPUT_DIR'] = '/tmp/test_output'
    yield app

@pytest.fixture()
def client(app):
    return app.test_client()
```

### Testing SSE Endpoint (Non-Streaming — Parse Pre-queued Events)
```python
# SSE streaming responses hang the test client if the generator blocks.
# Testing approach: pre-populate _sse_queue, then read response with response_streamed=False
# OR mock the queue to send sentinel and run_complete.

def test_stream_delivers_events(client, monkeypatch):
    import queue
    import app as app_module

    q = queue.Queue()
    q.put('event: file_done\ndata: {"filename": "a.tif"}\n\n')
    q.put('event: run_complete\ndata: {}\n\n')
    monkeypatch.setattr(app_module, '_sse_queue', q)
    monkeypatch.setattr(app_module._run_active, 'is_set', lambda: True)

    # Flask test client with stream_with_context — read with iter_encoded:
    with client.get('/stream') as resp:
        # Read chunks until exhausted
        chunks = list(resp.iter_encoded())

    text = b''.join(chunks).decode()
    assert 'event: file_done' in text
    assert 'event: run_complete' in text
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flask-SSE (Redis-backed) | queue.Queue (no-deps) | ~2020 | Eliminates Redis dependency for single-server use |
| Flask's `app.run(threaded=False)` | `threaded=True` (default in Flask 3.x dev) | Flask 1.0 | Request-handling threads don't block SSE stream |
| `ProcessPoolExecutor` for web worker progress | `threading.Thread` + `process_tiff()` loop | macOS Python 3.8 | Avoids spawn+fork issues; enables progressive SSE |
| `werkzeug.__version__` attribute | `importlib.metadata.version('werkzeug')` | Werkzeug 3.x | `__version__` removed from Werkzeug 3.x module |

**Deprecated/outdated:**
- `flask.Flask.run(use_reloader=True)` with background threads: reloader forks the process, creating two Flask instances each with their own module-level state. Disable reloader when using background threads: `app.run(use_reloader=False)`.
- `flask-sse` package: requires Redis pub/sub — overkill for this project.

---

## Open Questions

1. **Progressive SSE vs. run_batch() reuse**
   - What we know: CONTEXT.md says "reuse pipeline.run_batch()". SSE success criterion requires events arrive WHILE OCR is running. `run_batch()` accumulates all results and returns them at the end, so it cannot post progressive SSE events per file.
   - What's unclear: Does "reuse run_batch()" mean call it with a one-file list per iteration (sequential, no ProcessPoolExecutor parallelism), or does it mean call it once with all files and post events from file_records after the fact (violating the progressive criterion)?
   - Recommendation: Planner should resolve by calling `process_tiff()` directly in a per-file loop in the background thread. This "reuses pipeline functions" without the batch-return limitation. Document the decision in the plan.

2. **Output directory configuration in app.py**
   - What we know: pipeline.py takes `--output` as a CLI arg. app.py needs to know the output directory to check `alto/` for skip logic and write to `uploads/`.
   - What's unclear: Is output_dir hardcoded in app.py, passed as an environment variable, or a CLI arg to `python app.py`?
   - Recommendation: Accept `--output` as a CLI arg to `app.py` (mirrors CLI convention). Store in `app.config['OUTPUT_DIR']`.

3. **XSD schema loading in app.py**
   - What we know: `pipeline.load_xsd()` must be called once before validation. Phase 9 doesn't do validation (that is a post-OCR step added in Phase 3 of the CLI). For Phase 9, skip validation entirely to keep scope clean.
   - Recommendation: Do NOT call `validate_batch()` in Phase 9. Keep the OCR worker to: process → SSE event. Add validation in a later phase if needed for the web UI.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-flask 1.3.0 |
| Config file | none — see Wave 0 |
| Quick run command | `pytest tests/test_app.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |
| Estimated runtime | ~5 seconds (mocked OCR; no real TIFF processing) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROC-03 | Already-processed TIFF (alto/ exists) is skipped automatically on upload and run | integration | `pytest tests/test_app.py::test_skip_already_processed -x` | Wave 0 gap |
| PROC-04 | A TIFF that fails OCR posts `event: file_done` with `state=error` without stopping remaining files | integration | `pytest tests/test_app.py::test_error_isolation -x` | Wave 0 gap |

**Note on SSE testing:** Flask test client does not natively support blocking SSE generators without hanging. Tests for SSE correctness should either (a) pre-populate `_sse_queue` via monkeypatch and read the response synchronously, or (b) run the OCR worker in a thread and join it before asserting on collected events. Pattern (a) is preferred for unit-level SSE format tests. Pattern (b) is preferred for integration tests with real (tiny) TIFFs.

### Nyquist Sampling Rate
- **Minimum sample interval:** After every committed task → run: `pytest tests/test_app.py -x -q`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~5 seconds

### Wave 0 Gaps (must be created before implementation)
- [ ] `tests/test_app.py` — covers PROC-03 (skip logic) and PROC-04 (error isolation)
- [ ] `tests/conftest.py` update — add `app` and `client` fixtures for phase 9 (pytest-flask pattern)
- [ ] Add `flask` and `werkzeug` to `requirements.txt`

---

## Sources

### Primary (HIGH confidence)
- Flask 3.1.x official docs (`flask.palletsprojects.com/en/stable/patterns/streaming/`) — streaming Response, stream_with_context
- Flask 3.1.x official docs (`flask.palletsprojects.com/en/stable/patterns/fileuploads/`) — file upload, secure_filename, request.files.getlist()
- Flask 3.1.x official docs (`flask.palletsprojects.com/en/stable/testing/`) — test client, file upload in tests
- pipeline.py source code — run_batch() return signature, process_tiff() API, count_words(), ALTO21_NS, load_xsd()
- Python stdlib docs — `queue.Queue`, `threading.Lock`, `threading.Event`
- Direct version check: Flask 3.1.3, Werkzeug 3.1.6, pytest 9.0.2, pytest-flask 1.3.0

### Secondary (MEDIUM confidence)
- Max Halford Flask SSE no-deps pattern (`maxhalford.github.io/blog/flask-sse-no-deps/`) — Queue-based announcer, format_sse, listener management; verified against Flask docs
- Flask threading guide (`vmois.dev/python-flask-background-thread/`) — app context in threads, daemon=True pattern; verified against Flask docs
- Python `concurrent.futures` docs — ProcessPoolExecutor macOS spawn context safety

### Tertiary (LOW confidence)
- WebSearch: macOS ProcessPoolExecutor + threading.Thread interaction — multiple sources agree on spawn-context risks; STATE.md project decision confirms the concern
- SSE test client blocking behavior — reported in pytest-flask GitHub issues; workaround (monkeypatch queue) is LOW confidence until verified against actual test run

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Flask 3.1.3 and Werkzeug 3.1.6 verified by direct install; pytest/pytest-flask verified
- Architecture (SSE + Queue pattern): HIGH — verified against official Flask docs and Max Halford reference implementation
- Architecture (process_tiff() loop vs run_batch()): MEDIUM — based on source code analysis; open question flagged for planner
- Pitfalls: MEDIUM — stem normalization and app context issues verified; ProcessPoolExecutor macOS issue confirmed by STATE.md project decision

**Research date:** 2026-02-27
**Valid until:** 2026-03-29 (Flask 3.x is stable; no breaking changes expected within 30 days)
