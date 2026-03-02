"""app.py — Zeitschriften-OCR Web Viewer server.

Flask 3.1 application with POST /upload, POST /run, GET /stream.
Module-level job state protected by threading.Lock.
Background _ocr_worker calls pipeline.process_tiff() sequentially
for progressive SSE delivery.
"""
import argparse
import contextlib
import importlib
import json
import os
import queue
import tempfile
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file, stream_with_context
from PIL import Image
from werkzeug.utils import secure_filename

import mets
import pipeline
import search
import vlm

# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

_VALID_BACKENDS = frozenset({'openai_compatible'})


def _load_settings(output_dir: Path) -> dict:
    """Load output/settings.json. Returns {} if missing or unreadable."""
    settings_path = output_dir / 'settings.json'
    try:
        return json.loads(settings_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_settings(output_dir: Path, settings: dict) -> None:
    """Atomically write settings dict to output/settings.json."""
    settings_path = output_dir / 'settings.json'
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(output_dir), suffix='.tmp')
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp_path, str(settings_path))
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def _make_provider_from_settings(settings: dict):
    """Build a SegmentationProvider from persisted settings dict.

    Returns None if settings are incomplete.
    """
    backend = settings.get('backend', '')
    base_url = settings.get('base_url', '').strip()
    api_key = settings.get('api_key', '').strip()
    model = settings.get('model', '').strip()
    if backend not in _VALID_BACKENDS or not model:
        return None
    return vlm.get_provider('openai_compatible', model, api_key, base_url=base_url)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

OUTPUT_DIR_DEFAULT = './output'
UPLOAD_SUBDIR = 'uploads'

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_job_lock = threading.Lock()
_jobs: dict = {}          # stem → {filename, state, word_count, elapsed_time, error_msg}
_sse_queue: queue.Queue | None = None
_run_active = threading.Event()

app = Flask(__name__)
app.config['OUTPUT_DIR'] = OUTPUT_DIR_DEFAULT   # default; overridden by --output CLI arg

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _compute_jpeg_dims(tiff_path: Path) -> tuple[int, int]:
    """Compute the JPEG dimensions that Pillow would produce for this TIFF.

    Uses the same MAX_PX=1600 longest-side scale logic as serve_image().
    Called by serve_alto() so it can return jpeg_width/jpeg_height without
    requiring the JPEG cache to exist first.

    Returns (jpeg_width, jpeg_height) as integers.
    """
    MAX_PX = 1600
    with Image.open(str(tiff_path)) as img:
        w, h = img.size
    longest = max(w, h)
    if longest > MAX_PX:
        scale = MAX_PX / longest
        return round(w * scale), round(h * scale)
    return w, h


def _ocr_worker(tiff_paths: list, output_dir: Path, lang: str, psm: int, padding: int) -> None:
    """Background worker: process each TIFF sequentially and post SSE events.

    Runs in a daemon threading.Thread. Uses pipeline.process_tiff() directly
    (not ProcessPoolExecutor) so each file completion can be streamed via SSE.

    Args:
        tiff_paths: List of Path objects for TIFF files to process.
        output_dir: Root output directory (alto/ subdirectory written here).
        lang: Tesseract language code.
        psm: Tesseract page segmentation mode.
        padding: Crop border padding in pixels.
    """
    try:
        for tiff_path in tiff_paths:
            stem = tiff_path.stem.lower()
            alto_path = output_dir / 'alto' / (stem + '.xml')
            t0 = time.monotonic()

            if alto_path.exists():
                # Already processed — skip
                elapsed = 0.0
                with _job_lock:
                    _jobs[stem] = {
                        'filename': tiff_path.name,
                        'state': 'skipped',
                        'word_count': None,
                        'elapsed_time': elapsed,
                        'error_msg': None,
                    }
                event_data = {
                    'stem': stem,
                    'state': 'skipped',
                    'word_count': None,
                    'elapsed_time': elapsed,
                }
                if _sse_queue is not None:
                    _sse_queue.put(_format_sse('file_done', event_data))
                continue

            try:
                pipeline.process_tiff(
                    tiff_path,
                    output_dir,
                    lang=lang,
                    psm=psm,
                    padding=padding,
                    no_crop=False,
                    adaptive_threshold=False,
                )
                elapsed = time.monotonic() - t0

                # Read word count from written ALTO file
                word_count = None
                if alto_path.exists():
                    try:
                        from lxml import etree as _etree
                        root = _etree.parse(str(alto_path)).getroot()
                        word_count = pipeline.count_words(root, pipeline.ALTO21_NS)
                    except Exception:
                        word_count = None

                with _job_lock:
                    _jobs[stem] = {
                        'filename': tiff_path.name,
                        'state': 'done',
                        'word_count': word_count,
                        'elapsed_time': round(elapsed, 1),
                        'error_msg': None,
                    }
                event_data = {
                    'stem': stem,
                    'state': 'done',
                    'word_count': word_count,
                    'elapsed_time': round(elapsed, 1),
                }

            except Exception as exc:
                elapsed = time.monotonic() - t0
                error_msg = str(exc)
                with _job_lock:
                    _jobs[stem] = {
                        'filename': tiff_path.name,
                        'state': 'error',
                        'word_count': None,
                        'elapsed_time': round(elapsed, 1),
                        'error_msg': error_msg,
                    }
                event_data = {
                    'stem': stem,
                    'state': 'error',
                    'error_msg': error_msg,
                    'elapsed_time': round(elapsed, 1),
                }

            if _sse_queue is not None:
                _sse_queue.put(_format_sse('file_done', event_data))

        # Signal that the entire run is complete
        if _sse_queue is not None:
            _sse_queue.put(_format_sse('run_complete', {'total': len(tiff_paths)}))

    finally:
        _run_active.clear()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.before_request
def reject_path_traversal():
    """Return 400 JSON for any request path that contains '..' sequences.

    Flask's routing won't match <stem> variables containing slashes, so a URL
    like /image/../etc/passwd gets a 404 from the router before reaching the
    route handler.  Checking the raw path here ensures we return 400 (not 404)
    for traversal attempts on /image/ and /alto/ endpoints, satisfying the
    security contract tested in test_path_traversal_dot_dot.
    """
    from flask import request as _req
    if '..' in _req.path:
        return jsonify({'error': 'invalid path'}), 400


@app.post('/upload')
def upload():
    """Stage uploaded TIFF files and mark already-processed ones as done."""
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'no files provided'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    upload_dir = output_dir / UPLOAD_SUBDIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for f in files:
        if not f.filename:
            continue

        filename = secure_filename(f.filename)

        if Path(filename).suffix.lower() not in ('.tif', '.tiff'):
            results.append({
                'filename': filename,
                'status': 'rejected',
                'reason': 'not a TIFF file',
                'already_processed': False,
            })
            continue

        # Normalize stem to lowercase — pipeline writes lowercase output paths
        stem = Path(filename).stem.lower()

        # Save the uploaded file
        f.save(upload_dir / filename)

        # Check if already processed
        alto_path = output_dir / 'alto' / (stem + '.xml')
        already_done = alto_path.exists()

        with _job_lock:
            _jobs[stem] = {
                'filename': filename,
                'state': 'done' if already_done else 'pending',
                'word_count': None,
                'elapsed_time': None,
                'error_msg': None,
            }

        results.append({
            'filename': filename,
            'status': 'staged',
            'already_processed': already_done,
        })

    return jsonify({'files': results}), 200


@app.post('/run')
def run():
    """Start OCR processing of all pending files in a background thread."""
    if _run_active.is_set():
        return jsonify({'error': 'a run is already in progress'}), 409

    output_dir = Path(app.config['OUTPUT_DIR'])
    lang = app.config.get('LANG', 'deu')
    psm = app.config.get('PSM', 1)
    padding = app.config.get('PADDING', 50)
    upload_dir = output_dir / UPLOAD_SUBDIR

    with _job_lock:
        pending = [stem for stem, job in _jobs.items() if job['state'] == 'pending']

    if not pending:
        return jsonify({'error': 'no pending files'}), 400

    # Set active flag and reset SSE queue before launching thread
    _run_active.set()
    global _sse_queue
    with _job_lock:
        _sse_queue = queue.Queue()

    # Build tiff_paths from pending stems
    tiff_paths = []
    with _job_lock:
        for stem in pending:
            job = _jobs.get(stem)
            if job:
                tiff_paths.append(upload_dir / job['filename'])

    thread = threading.Thread(
        target=_ocr_worker,
        args=(tiff_paths, output_dir, lang, psm, padding),
        daemon=True,
    )
    thread.start()

    return jsonify({'status': 'started', 'files': pending}), 202


@app.get('/stream')
def stream():
    """Stream SSE events from the OCR worker."""
    def generate():
        local_q = _sse_queue
        if local_q is None:
            return
        while True:
            try:
                msg = local_q.get(timeout=30)
                yield msg
                if msg.startswith('event: run_complete'):
                    break
            except queue.Empty:
                yield ': keepalive\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.get('/image/<stem>')
def serve_image(stem):
    """Serve a scaled JPEG for the requested TIFF stem.

    Caches the rendered JPEG at output_dir/jpegcache/<stem>.jpg.
    Returns 400 for path traversal, 404 if TIFF absent, 500 on render failure.
    """
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    cache_dir = output_dir / 'jpegcache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (stem + '.jpg')

    # Serve from cache if available
    if cache_path.exists():
        return send_file(cache_path, mimetype='image/jpeg')

    # Locate the source TIFF — try _jobs dict first (populated by /upload),
    # then scan uploads/ for case-insensitive match (handles server restart).
    upload_dir = output_dir / UPLOAD_SUBDIR
    tiff_path = None
    with _job_lock:
        job = _jobs.get(stem)
    if job:
        candidate = upload_dir / job['filename']
        if candidate.exists():
            tiff_path = candidate
    if tiff_path is None:
        # Fallback: scan uploads/ for <stem>.tif or <stem>.tiff (case-insensitive)
        if upload_dir.exists():
            for candidate in upload_dir.iterdir():
                if candidate.suffix.lower() in ('.tif', '.tiff'):
                    if candidate.stem.lower() == stem.lower():
                        tiff_path = candidate
                        break
    if tiff_path is None:
        # Final fallback: scan INPUT_DIR (CLI-processed TIFFs not uploaded via web UI)
        input_dir_str = app.config.get('INPUT_DIR')
        if input_dir_str:
            input_dir = Path(input_dir_str)
            if input_dir.exists():
                for candidate in input_dir.iterdir():
                    if candidate.suffix.lower() in ('.tif', '.tiff'):
                        if candidate.stem.lower() == stem.lower():
                            tiff_path = candidate
                            break
    if tiff_path is None:
        return jsonify({'error': 'not found', 'stem': stem}), 404

    # Render JPEG from TIFF
    MAX_PX = 1600
    try:
        img = Image.open(str(tiff_path))
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        w, h = img.size
        longest = max(w, h)
        if longest > MAX_PX:
            scale = MAX_PX / longest
            img = img.resize(
                (round(w * scale), round(h * scale)),
                Image.Resampling.LANCZOS,
            )
        img.save(str(cache_path), format='JPEG', quality=85)
    except Exception as exc:
        return jsonify({'error': 'render failed', 'detail': str(exc)}), 500

    return send_file(cache_path, mimetype='image/jpeg')


@app.get('/alto/<stem>')
def serve_alto(stem):
    """Return flat word array and page/JPEG dimensions from ALTO XML.

    Parses ALTO XML on every request (no disk cache — Phase 12 edits XML directly).
    Returns 400 for path traversal, 404 if ALTO absent, 500 on parse/structure failure.

    Response shape:
      {
        page_width: int, page_height: int,
        jpeg_width: int, jpeg_height: int,
        words: [{id, content, hpos, vpos, width, height, confidence}, ...]
      }
    confidence is float or null (null when WC attribute absent, NOT coerced to 0).
    """
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_path = output_dir / 'alto' / (stem + '.xml')
    if not alto_path.exists():
        return jsonify({'error': 'not found', 'stem': stem}), 404

    try:
        from lxml import etree
        root = etree.parse(str(alto_path)).getroot()
    except Exception as exc:
        return jsonify({'error': 'parse failed', 'detail': str(exc)}), 500

    ns = pipeline.ALTO21_NS  # 'http://schema.ccs-gmbh.com/ALTO'

    # Page dimensions
    page = root.find(f'.//{{{ns}}}Page')
    if page is None:
        return jsonify({'error': 'no Page element in ALTO XML', 'stem': stem}), 500
    page_width = int(page.get('WIDTH', 0))
    page_height = int(page.get('HEIGHT', 0))
    if page_width == 0 or page_height == 0:
        return jsonify({'error': 'Page WIDTH/HEIGHT missing or zero', 'stem': stem}), 500

    # JPEG dimensions — from cache if available, else compute from TIFF
    cache_path = output_dir / 'jpegcache' / (stem + '.jpg')
    if cache_path.exists():
        try:
            with Image.open(str(cache_path)) as _img:
                jpeg_width, jpeg_height = _img.size
        except Exception:
            jpeg_width, jpeg_height = 0, 0
    else:
        # Compute from TIFF (avoids ordering dependency between /image/ and /alto/)
        upload_dir = output_dir / UPLOAD_SUBDIR
        tiff_path = None
        with _job_lock:
            job = _jobs.get(stem)
        if job:
            candidate = upload_dir / job['filename']
            if candidate.exists():
                tiff_path = candidate
        if tiff_path is None and upload_dir.exists():
            for candidate in upload_dir.iterdir():
                if candidate.suffix.lower() in ('.tif', '.tiff'):
                    if candidate.stem.lower() == stem.lower():
                        tiff_path = candidate
                        break
        if tiff_path is not None:
            try:
                jpeg_width, jpeg_height = _compute_jpeg_dims(tiff_path)
            except Exception:
                jpeg_width, jpeg_height = 0, 0
        else:
            jpeg_width, jpeg_height = 0, 0

    # Flat word array — all String elements in document order
    words = []
    for i, elem in enumerate(root.iter(f'{{{ns}}}String')):
        wc_raw = elem.get('WC')
        words.append({
            'id': f'w{i}',
            'content': elem.get('CONTENT', ''),
            'hpos': int(elem.get('HPOS', 0)),
            'vpos': int(elem.get('VPOS', 0)),
            'width': int(elem.get('WIDTH', 0)),
            'height': int(elem.get('HEIGHT', 0)),
            'confidence': float(wc_raw) if wc_raw is not None else None,
        })

    return jsonify({
        'page_width': page_width,
        'page_height': page_height,
        'jpeg_width': jpeg_width,
        'jpeg_height': jpeg_height,
        'words': words,
    })


@app.post('/save/<stem>')
def save_word(stem):
    """Persist a corrected word CONTENT attribute back to the ALTO XML file on disk.

    Request body (JSON): {"word_id": "w3", "content": "corrected text"}
    word_id is the positional index string ("w0", "w1", ...) matching GET /alto/<stem> response.

    Atomic write: writes to a tempfile in the same directory, then os.replace() over original.
    XSD gate: serialized bytes are validated before write; 422 if invalid (no disk write).

    Returns:
        200 {"status": "ok"} on success
        400 {"error": "word_id required"} / {"error": "content required"} on missing fields
        422 {"error": "Save failed — invalid content"} on empty/whitespace content or XSD failure
        404 {"error": "not found", "stem": "..."} when ALTO file absent
        404 {"error": "word not found", "word_id": "..."} when word_id index out of range
        500 {"error": "parse failed", "detail": "..."} on XML parse error
        500 {"error": "write failed", "detail": "..."} on I/O failure
    """
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    body = request.get_json(silent=True) or {}
    word_id = body.get('word_id')
    content = body.get('content')

    if word_id is None:
        return jsonify({'error': 'word_id required'}), 400
    if content is None:
        return jsonify({'error': 'content required'}), 400
    if not str(content).strip():
        return jsonify({'error': 'Save failed \u2014 invalid content'}), 422

    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_path = output_dir / 'alto' / (stem + '.xml')
    if not alto_path.exists():
        return jsonify({'error': 'not found', 'stem': stem}), 404

    try:
        from lxml import etree
        root = etree.parse(str(alto_path)).getroot()
    except Exception as exc:
        return jsonify({'error': 'parse failed', 'detail': str(exc)}), 500

    ns = pipeline.ALTO21_NS
    strings = list(root.iter(f'{{{ns}}}String'))

    # Parse word_id: expect "w{N}" format
    try:
        idx = int(word_id.lstrip('w'))
    except (ValueError, AttributeError):
        return jsonify({'error': 'word not found', 'word_id': word_id}), 404
    if idx < 0 or idx >= len(strings):
        return jsonify({'error': 'word not found', 'word_id': word_id}), 404

    strings[idx].set('CONTENT', str(content))

    # XSD validation gate — serialize to bytes, validate, then write atomically
    out_bytes = etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)

    xsd = pipeline.load_xsd(pipeline.SCHEMA_PATH)
    if xsd is not None:
        try:
            doc = etree.fromstring(out_bytes)
            if not xsd.validate(doc):
                return jsonify({'error': 'Save failed \u2014 invalid content'}), 422
        except Exception:
            return jsonify({'error': 'Save failed \u2014 invalid content'}), 422

    # Atomic write: temp file in same directory, then os.replace
    tmp_fd, tmp_path_str = tempfile.mkstemp(
        dir=str(alto_path.parent), suffix='.tmp'
    )
    try:
        with os.fdopen(tmp_fd, 'wb') as fh:
            fh.write(out_bytes)
        os.replace(tmp_path_str, str(alto_path))
    except Exception as exc:
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        return jsonify({'error': 'write failed', 'detail': str(exc)}), 500

    return jsonify({'status': 'ok'}), 200


@app.get('/files')
def list_files():
    """Return alphabetically sorted list of ALTO stems in output/alto/."""
    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_dir = output_dir / 'alto'
    if not alto_dir.exists():
        return jsonify({'stems': []})
    stems = sorted(p.stem for p in alto_dir.glob('*.xml'))
    return jsonify({'stems': stems})


@app.post('/segment/<stem>')
def segment_page(stem):
    """Trigger VLM article segmentation for the given TIFF stem.

    Reads JPEG from jpegcache, calls the configured VLM provider,
    parses regions, writes output/segments/<stem>.json, returns result.

    Status codes:
        200: success — {"stem", "provider", "model", "segmented_at", "regions"}
        400: path traversal in stem
        404: JPEG not in jpegcache (open the viewer for this file first)
        503: VLM provider not configured (start app with --vlm-provider)
        502: VLM API call failed
    """
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    # --- Provider resolution ---
    # 1. Read from settings.json (web UI configured)
    output_dir = Path(app.config['OUTPUT_DIR'])
    settings = _load_settings(output_dir)
    provider = _make_provider_from_settings(settings)

    if provider is None:
        # 2. Fall back to CLI flags in app.config
        provider_name = app.config.get('VLM_PROVIDER', '')
        if not provider_name:
            return jsonify({
                'error': 'Article segmentation requires a VLM provider. Configure it in Settings or restart the server with --vlm-provider claude (or openai).'
            }), 503
        model = app.config.get('VLM_MODEL', 'claude-opus-4-6')
        api_key = (
            app.config.get('VLM_API_KEY')
            or os.environ.get('ANTHROPIC_API_KEY')
            or os.environ.get('OPENAI_API_KEY', '')
        )
        try:
            provider = vlm.get_provider(provider_name, model, api_key)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
    else:
        # Provider came from settings.json
        provider_name = settings.get('backend', 'openai_compatible')
        model = settings.get('model', '')

    jpeg_path = output_dir / 'jpegcache' / (stem + '.jpg')
    if not jpeg_path.exists():
        return jsonify({
            'error': 'image not found — open the viewer for this file first',
            'stem': stem,
        }), 404

    try:
        regions = provider.segment(jpeg_path)
    except Exception as exc:
        return jsonify({'error': 'VLM API call failed', 'detail': str(exc)}), 502

    from datetime import datetime, timezone
    segmented_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    result = {
        'stem': stem,
        'provider': provider_name,
        'model': model,
        'segmented_at': segmented_at,
        'regions': regions,
    }

    seg_dir = output_dir / 'segments'
    seg_dir.mkdir(parents=True, exist_ok=True)
    seg_path = seg_dir / (stem + '.json')
    seg_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    # Auto-index into FTS5 search DB
    search.init_db(output_dir)
    search.index_stem(output_dir, stem, regions)

    return jsonify(result), 200


@app.get('/segment/<stem>')
def get_segment(stem):
    """Return stored segmentation result for the given stem.

    Returns 404 if segmentation has not been run for this stem.
    """
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    seg_path = output_dir / 'segments' / (stem + '.json')
    if not seg_path.exists():
        return jsonify({'error': 'not found', 'stem': stem}), 404

    try:
        return jsonify(json.loads(seg_path.read_text()))
    except Exception as exc:
        return jsonify({'error': 'parse failed', 'detail': str(exc)}), 500


@app.get('/articles/<stem>')
def get_articles(stem):
    """Return article region list for the given stem from segment JSON.

    Reads output/segments/<stem>.json directly — no DB lookup required.
    Returns 400 for path traversal, 404 if not yet segmented.
    """
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    seg_path = output_dir / 'segments' / (stem + '.json')
    if not seg_path.exists():
        return jsonify({'error': 'not segmented', 'stem': stem}), 404

    try:
        data = json.loads(seg_path.read_text())
    except Exception as exc:
        return jsonify({'error': 'parse failed', 'detail': str(exc)}), 500

    return jsonify({'stem': stem, 'regions': data.get('regions', [])})


@app.get('/api/search')
def search_articles():
    """Full-text search across all indexed article titles (JSON API).

    Query param: q (search string)
    Returns {"results": [{stem, region_id, type, title}, ...]} ranked by relevance.
    Returns empty results list for empty q or missing search DB.
    """
    q = request.args.get('q', '').strip()
    output_dir = Path(app.config['OUTPUT_DIR'])
    results = search.query(output_dir, q)
    return jsonify({'results': results})


@app.get('/search')
def search_page():
    """Serve the article search results page."""
    return render_template('search.html')


@app.get('/mets')
def export_mets():
    """Generate and return METS/MODS XML for all processed pages.

    Reads ALTO files from output_dir/alto/ and segment JSON from output_dir/segments/.
    Returns XML as a downloadable attachment (Content-Disposition: attachment).
    Returns 204 if no ALTO files exist yet.
    Returns 500 on builder exception.

    issue_title can be set via --issue-title CLI arg stored in app.config['ISSUE_TITLE'].
    """
    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_dir = output_dir / 'alto'

    if not alto_dir.exists() or not any(alto_dir.glob('*.xml')):
        return Response('', status=204)

    issue_title = app.config.get('ISSUE_TITLE', '')

    try:
        xml_bytes = mets.build_mets(output_dir, issue_title=issue_title)
    except Exception as exc:
        return jsonify({'error': 'METS build failed', 'detail': str(exc)}), 500

    return Response(
        xml_bytes,
        status=200,
        mimetype='application/xml',
        headers={'Content-Disposition': 'attachment; filename="mets.xml"'},
    )


@app.get('/settings')
def get_settings():
    """Return current VLM settings from output/settings.json.

    Returns {} if no settings file exists yet.
    """
    output_dir = Path(app.config['OUTPUT_DIR'])
    return jsonify(_load_settings(output_dir))


@app.post('/settings')
def post_settings():
    """Persist VLM settings to output/settings.json.

    Expected JSON body:
      { "backend": "openai_compatible",
        "base_url": "https://...",
        "api_key": "...",
        "model": "..." }

    Returns 400 if backend is missing or not a supported value.
    """
    body = request.get_json(silent=True) or {}
    backend = body.get('backend', '')
    if backend not in _VALID_BACKENDS:
        return jsonify({'error': f'backend must be one of: {", ".join(sorted(_VALID_BACKENDS))}'}), 400

    settings = {
        'backend': backend,
        'base_url': str(body.get('base_url', '')).strip(),
        'api_key': str(body.get('api_key', '')).strip(),
        'model': str(body.get('model', '')).strip(),
    }
    output_dir = Path(app.config['OUTPUT_DIR'])
    try:
        _save_settings(output_dir, settings)
    except Exception as exc:
        return jsonify({'error': 'Failed to save settings', 'detail': str(exc)}), 500
    return jsonify({'ok': True})


@app.get('/settings/models')
def get_settings_models():
    """Fetch available models from an OpenAI-compatible endpoint.

    Query params: base_url, api_key
    Returns {"models": ["model-a", "model-b", ...]} on success.
    Returns 400 if params missing, 502 if remote API errors.
    """
    base_url = request.args.get('base_url', '').strip()
    api_key = request.args.get('api_key', '').strip()
    if not base_url:
        return jsonify({'error': 'base_url query param is required'}), 400

    try:
        import openai  # lazy import
        client = openai.OpenAI(base_url=base_url, api_key=api_key or 'none')
        model_list = client.models.list()
        model_ids = sorted(m.id for m in model_list.data)
        return jsonify({'models': model_ids})
    except Exception as exc:
        return jsonify({'error': 'Failed to fetch models', 'detail': str(exc)}), 502


@app.get('/')
def index():
    """Serve the upload and progress dashboard."""
    return render_template('upload.html')


@app.get('/viewer/')
@app.get('/viewer')
def viewer_index():
    """Serve the viewer without a specific stem — JS auto-loads the first file."""
    return render_template('viewer.html', initial_stem=None)


@app.get('/viewer/<stem>')
def viewer(stem):
    """Serve the side-by-side viewer for a specific TIFF stem."""
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400
    return render_template('viewer.html', initial_stem=stem)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Zeitschriften-OCR Web Viewer')
    parser.add_argument('--output', default='./output', help='Output directory (default: ./output)')
    parser.add_argument('--lang', default='deu', help='Tesseract language (default: deu)')
    parser.add_argument('--psm', type=int, default=1, help='Page segmentation mode (default: 1)')
    parser.add_argument('--padding', type=int, default=50, help='Crop padding in pixels (default: 50)')
    parser.add_argument('--port', type=int, default=5000, help='Port (default: 5000)')
    parser.add_argument('--input', default=None, help='Input TIFF directory (for CLI-processed files)')
    parser.add_argument('--vlm-provider', default=None,
                        help='VLM provider for article segmentation: claude or openai')
    parser.add_argument('--vlm-model', default=None,
                        help='VLM model name (default: claude-opus-4-6 for claude, gpt-4o for openai)')
    parser.add_argument('--vlm-api-key', default=None,
                        help='API key (fallback: ANTHROPIC_API_KEY or OPENAI_API_KEY env vars)')
    parser.add_argument('--issue-title', default='',
                        help='Issue title for METS/MODS descriptive metadata')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'uploads').mkdir(exist_ok=True)
    (output_dir / 'alto').mkdir(exist_ok=True)
    (output_dir / 'jpegcache').mkdir(exist_ok=True)

    app.config['OUTPUT_DIR'] = str(output_dir)
    if args.input:
        app.config['INPUT_DIR'] = str(Path(args.input).resolve())
    app.config['LANG'] = args.lang
    app.config['PSM'] = args.psm
    app.config['PADDING'] = args.padding

    if args.vlm_provider:
        app.config['VLM_PROVIDER'] = args.vlm_provider
    if args.vlm_model:
        app.config['VLM_MODEL'] = args.vlm_model
    elif args.vlm_provider == 'openai':
        app.config['VLM_MODEL'] = 'gpt-4o'
    else:
        app.config['VLM_MODEL'] = 'claude-opus-4-6'
    if args.vlm_api_key:
        app.config['VLM_API_KEY'] = args.vlm_api_key
    app.config['ISSUE_TITLE'] = args.issue_title

    app.run(host='0.0.0.0', port=args.port, threaded=True, use_reloader=False)
