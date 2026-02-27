"""app.py — Zeitschriften-OCR Web Viewer server.

Flask 3.1 application with POST /upload, POST /run, GET /stream.
Module-level job state protected by threading.Lock.
Background _ocr_worker calls pipeline.process_tiff() sequentially
for progressive SSE delivery.
"""
import argparse
import importlib
import json
import queue
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, stream_with_context
from PIL import Image
from werkzeug.utils import secure_filename

import pipeline

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
            stem = tiff_path.stem
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
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'uploads').mkdir(exist_ok=True)
    (output_dir / 'alto').mkdir(exist_ok=True)
    (output_dir / 'jpegcache').mkdir(exist_ok=True)

    app.config['OUTPUT_DIR'] = str(output_dir)
    app.config['LANG'] = args.lang
    app.config['PSM'] = args.psm
    app.config['PADDING'] = args.padding

    app.run(host='0.0.0.0', port=args.port, threaded=True, use_reloader=False)
