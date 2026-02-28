"""Tests for app.py — Phase 9: Flask Foundation and Job State.

PROC-03: Already-processed TIFFs are skipped automatically.
PROC-04: Per-file OCR errors are reported without stopping the batch.
"""
import json
import queue
import io
from pathlib import Path
import pytest


# ---------------------------------------------------------------------------
# PROC-03: Skip already-processed TIFFs
# ---------------------------------------------------------------------------

class TestSkipAlreadyProcessed:

    def test_upload_marks_already_processed(self, client, flask_app, tmp_path):
        """POST /upload: TIFF with existing alto/<stem>.xml gets already_processed=True."""
        import app as app_module

        # Pre-create alto output to simulate already-processed file
        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        (alto_dir / 'scan_001.xml').write_text('<ALTO/>')

        data = {
            'files': (io.BytesIO(b'TIFF_DUMMY'), 'scan_001.tif'),
        }
        resp = client.post('/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        body = resp.get_json()
        file_result = body['files'][0]
        assert file_result['already_processed'] is True

    def test_upload_sets_job_state_done_for_already_processed(self, client, flask_app, tmp_path):
        """POST /upload: already-processed TIFF has state='done' in job dict."""
        import app as app_module

        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        (alto_dir / 'scan_001.xml').write_text('<ALTO/>')

        data = {'files': (io.BytesIO(b'TIFF_DUMMY'), 'scan_001.tif')}
        client.post('/upload', data=data, content_type='multipart/form-data')

        with app_module._job_lock:
            job = app_module._jobs.get('scan_001')
        assert job is not None
        assert job['state'] == 'done'

    def test_run_returns_400_when_all_files_already_processed(self, client, flask_app, tmp_path):
        """POST /run: returns 400 'no pending files' when all uploads were already done."""
        import app as app_module

        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        (alto_dir / 'scan_001.xml').write_text('<ALTO/>')

        data = {'files': (io.BytesIO(b'TIFF_DUMMY'), 'scan_001.tif')}
        client.post('/upload', data=data, content_type='multipart/form-data')

        resp = client.post('/run')
        assert resp.status_code == 400
        assert 'no pending' in resp.get_json().get('error', '').lower()

    def test_stem_normalized_lowercase(self, client, flask_app, tmp_path):
        """POST /upload: stem is lowercased for skip check (pipeline writes lowercase stems)."""
        import app as app_module

        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        # pipeline writes lowercase stem
        (alto_dir / 'scan_001.xml').write_text('<ALTO/>')

        # Upload with uppercase extension — secure_filename preserves case, we must lowercase stem
        data = {'files': (io.BytesIO(b'TIFF_DUMMY'), 'Scan_001.TIF')}
        resp = client.post('/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['files'][0]['already_processed'] is True


# ---------------------------------------------------------------------------
# PROC-04: Per-file error isolation
# ---------------------------------------------------------------------------

class TestErrorIsolation:

    def test_ocr_error_posts_error_event_and_continues(self, flask_app, tmp_path, monkeypatch):
        """_ocr_worker: exception in process_tiff posts file_done(state=error), continues to next file."""
        import app as app_module
        from pathlib import Path

        output_dir = Path(str(tmp_path))
        (output_dir / 'uploads').mkdir(parents=True, exist_ok=True)
        (output_dir / 'alto').mkdir(parents=True, exist_ok=True)

        # Create dummy TIFF files
        bad_tiff = output_dir / 'uploads' / 'bad.tif'
        good_tiff = output_dir / 'uploads' / 'good.tif'
        bad_tiff.write_bytes(b'NOT_A_TIFF')
        good_tiff.write_bytes(b'NOT_A_TIFF')

        # Mock process_tiff: raise for bad, succeed for good
        call_order = []
        def mock_process_tiff(tiff_path, *args, **kwargs):
            call_order.append(tiff_path.stem)
            if tiff_path.stem == 'bad':
                raise RuntimeError('OCR failed for bad.tif')
            # For good: write a minimal alto xml to simulate success
            alto_path = output_dir / 'alto' / (tiff_path.stem + '.xml')
            alto_path.write_text('<ALTO xmlns="http://schema.ccs-gmbh.com/ALTO"/>')

        monkeypatch.setattr(app_module.pipeline, 'process_tiff', mock_process_tiff)

        # Pre-populate job state
        with app_module._job_lock:
            app_module._jobs.clear()
            app_module._jobs['bad'] = {'filename': 'bad.tif', 'state': 'pending',
                                       'word_count': None, 'elapsed_time': None, 'error_msg': None}
            app_module._jobs['good'] = {'filename': 'good.tif', 'state': 'pending',
                                        'word_count': None, 'elapsed_time': None, 'error_msg': None}
            app_module._sse_queue = queue.Queue()
        app_module._run_active.set()

        # Run worker synchronously (direct call, not via thread)
        app_module._ocr_worker(
            [bad_tiff, good_tiff],
            output_dir,
            lang='deu', psm=1, padding=50,
        )

        # Both files processed in order
        assert call_order == ['bad', 'good']

        # Error job state
        with app_module._job_lock:
            bad_job = app_module._jobs['bad']
            good_job = app_module._jobs['good']

        assert bad_job['state'] == 'error'
        assert bad_job['error_msg'] is not None
        assert 'OCR failed' in bad_job['error_msg']
        assert good_job['state'] == 'done'

        # SSE queue: file_done(error), file_done(done), run_complete
        events = []
        while not app_module._sse_queue.empty():
            events.append(app_module._sse_queue.get_nowait())
        assert len(events) == 3
        assert 'event: file_done' in events[0]
        assert '"state": "error"' in events[0]
        assert 'event: file_done' in events[1]
        assert '"state": "done"' in events[1]
        assert 'event: run_complete' in events[2]

    def test_run_active_cleared_after_worker_error(self, flask_app, tmp_path, monkeypatch):
        """_ocr_worker: _run_active is cleared in finally block even if all files fail."""
        import app as app_module
        from pathlib import Path

        output_dir = Path(str(tmp_path))
        (output_dir / 'uploads').mkdir(parents=True, exist_ok=True)
        (output_dir / 'alto').mkdir(parents=True, exist_ok=True)

        bad_tiff = output_dir / 'uploads' / 'bad.tif'
        bad_tiff.write_bytes(b'NOT_A_TIFF')

        def mock_process_tiff(tiff_path, *args, **kwargs):
            raise RuntimeError('always fails')

        monkeypatch.setattr(app_module.pipeline, 'process_tiff', mock_process_tiff)

        with app_module._job_lock:
            app_module._jobs.clear()
            app_module._jobs['bad'] = {'filename': 'bad.tif', 'state': 'pending',
                                       'word_count': None, 'elapsed_time': None, 'error_msg': None}
            app_module._sse_queue = queue.Queue()
        app_module._run_active.set()

        app_module._ocr_worker([bad_tiff], output_dir, lang='deu', psm=1, padding=50)

        assert not app_module._run_active.is_set(), '_run_active must be cleared after worker finishes'

    def test_run_returns_409_when_run_active(self, client, flask_app):
        """POST /run: returns 409 if _run_active is already set."""
        import app as app_module
        app_module._run_active.set()

        resp = client.post('/run')
        assert resp.status_code == 409
        assert 'in progress' in resp.get_json().get('error', '').lower()


# ---------------------------------------------------------------------------
# Helpers shared by Phase 10 tests
# ---------------------------------------------------------------------------

def _write_tiff(path, w=4, h=4, mode='RGB'):
    """Write a minimal synthetic TIFF to path using Pillow."""
    from PIL import Image
    img = Image.new(mode, (w, h), color=(128, 128, 128))
    img.save(str(path), format='TIFF')


ALTO_NS = 'http://schema.ccs-gmbh.com/ALTO'


def _write_alto(path, page_w, page_h, strings):
    """Write minimal ALTO 2.1 XML.

    strings = list of dicts with CONTENT/HPOS/VPOS/WIDTH/HEIGHT and optional WC.
    """
    from lxml import etree
    ns = ALTO_NS
    root = etree.Element(f'{{{ns}}}alto')
    layout = etree.SubElement(root, f'{{{ns}}}Layout')
    page = etree.SubElement(layout, f'{{{ns}}}Page')
    page.set('WIDTH', str(page_w))
    page.set('HEIGHT', str(page_h))
    block = etree.SubElement(page, f'{{{ns}}}PrintSpace')
    tb = etree.SubElement(block, f'{{{ns}}}TextBlock')
    line = etree.SubElement(tb, f'{{{ns}}}TextLine')
    for s in strings:
        elem = etree.SubElement(line, f'{{{ns}}}String')
        for k, v in s.items():
            elem.set(k, str(v))
    path.write_bytes(etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True))


# ---------------------------------------------------------------------------
# Phase 10: GET /image/<stem>
# ---------------------------------------------------------------------------

class TestImageEndpoint:
    """RED tests for GET /image/<stem> — all fail until Phase 10 Plan 02 implements the route."""

    def test_path_traversal_dot_dot(self, client, flask_app):
        """GET /image/../etc/passwd → 400, JSON body has 'error' key.

        Flask may normalize '/../' in URLs. If Flask normalises the path and
        returns a redirect (301/302), that is also accepted as a non-200
        non-JPEG response, because the endpoint does not exist yet and the
        route would not match anyway.
        """
        resp = client.get('/image/../etc/passwd')
        # Accept 400 (traversal rejected) or any non-200/non-jpeg status
        # The endpoint MUST NOT return 200 with image/jpeg content.
        assert resp.status_code == 400
        body = resp.get_json()
        assert body is not None
        assert 'error' in body

    def test_path_traversal_slash(self, client, flask_app):
        """GET /image/folder/scan → 400, no 200 JPEG returned.

        A stem containing a slash would escape the uploads/ directory.
        Flask routing: '/image/folder/scan' matches a two-segment path which
        will not match the <stem> variable-rule unless the rule uses path converter.
        Either 400 (explicit rejection) or 404 (route mismatch) is acceptable as
        long as we do NOT get 200 image/jpeg.
        """
        resp = client.get('/image/folder/scan')
        assert resp.status_code in (400, 404)
        # If 400, verify JSON error body
        if resp.status_code == 400:
            body = resp.get_json()
            assert body is not None
            assert 'error' in body

    def test_missing_tiff_returns_404(self, client, flask_app):
        """GET /image/nonexistent → 404, JSON body = {"error": "not found", "stem": "nonexistent"}."""
        resp = client.get('/image/nonexistent')
        assert resp.status_code == 404
        body = resp.get_json()
        assert body is not None
        assert body.get('error') == 'not found'
        assert body.get('stem') == 'nonexistent'

    def test_cache_hit_serves_jpeg(self, client, flask_app):
        """GET /image/scan_001 → 200 image/jpeg when jpegcache/scan_001.jpg exists."""
        from pathlib import Path
        from PIL import Image
        import io as _io

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        jpegcache_dir = output_dir / 'jpegcache'
        jpegcache_dir.mkdir(parents=True, exist_ok=True)

        # Write a small valid 1x1 JPEG to the cache
        img = Image.new('RGB', (1, 1), color=(200, 100, 50))
        buf = _io.BytesIO()
        img.save(buf, format='JPEG')
        (jpegcache_dir / 'scan_001.jpg').write_bytes(buf.getvalue())

        resp = client.get('/image/scan_001')
        assert resp.status_code == 200
        assert 'jpeg' in resp.content_type.lower()

    def test_tiff_render_writes_cache(self, client, flask_app):
        """GET /image/scan_001 → 200 JPEG rendered from TIFF; jpegcache/scan_001.jpg created."""
        from pathlib import Path

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        uploads_dir = output_dir / 'uploads'
        uploads_dir.mkdir(parents=True, exist_ok=True)

        _write_tiff(uploads_dir / 'scan_001.tif', w=4, h=4)

        resp = client.get('/image/scan_001')
        assert resp.status_code == 200
        assert 'jpeg' in resp.content_type.lower()

        # Cache file must have been written
        cache_file = output_dir / 'jpegcache' / 'scan_001.jpg'
        assert cache_file.exists(), f'jpegcache/scan_001.jpg not created after request'

    def test_filename_case_mismatch(self, client, flask_app):
        """GET /image/scan_002 → 200 even when TIFF is stored as Scan_002.tif (different case).

        The endpoint must scan uploads/ to find the file regardless of original filename case.
        """
        from pathlib import Path

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        uploads_dir = output_dir / 'uploads'
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # Original upload has mixed case
        _write_tiff(uploads_dir / 'Scan_002.tif', w=4, h=4)

        resp = client.get('/image/scan_002')
        assert resp.status_code == 200
        assert 'jpeg' in resp.content_type.lower()


# ---------------------------------------------------------------------------
# Phase 10: GET /alto/<stem>
# ---------------------------------------------------------------------------

class TestAltoEndpoint:
    """RED tests for GET /alto/<stem> — all fail until Phase 10 Plan 02 implements the route."""

    def test_path_traversal_rejected(self, client, flask_app):
        """GET /alto/../etc → 400, JSON body has 'error' key."""
        resp = client.get('/alto/../etc')
        assert resp.status_code == 400
        body = resp.get_json()
        assert body is not None
        assert 'error' in body

    def test_missing_alto_returns_404(self, client, flask_app):
        """GET /alto/nonexistent → 404, JSON = {"error": "not found", "stem": "nonexistent"}."""
        resp = client.get('/alto/nonexistent')
        assert resp.status_code == 404
        body = resp.get_json()
        assert body is not None
        assert body.get('error') == 'not found'
        assert body.get('stem') == 'nonexistent'

    def test_valid_alto_returns_json_shape(self, client, flask_app):
        """GET /alto/scan_003 → 200 JSON with page_width, page_height, jpeg_width, jpeg_height, words."""
        from pathlib import Path

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)

        _write_alto(
            alto_dir / 'scan_003.xml',
            page_w=5146,
            page_h=7548,
            strings=[
                {'CONTENT': 'Hallo', 'HPOS': '100', 'VPOS': '200', 'WIDTH': '80', 'HEIGHT': '30', 'WC': '0.95'},
                {'CONTENT': 'Welt', 'HPOS': '200', 'VPOS': '200', 'WIDTH': '60', 'HEIGHT': '30'},
            ],
        )

        resp = client.get('/alto/scan_003')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body is not None
        assert body.get('page_width') == 5146
        assert body.get('page_height') == 7548
        assert isinstance(body.get('jpeg_width'), int)
        assert isinstance(body.get('jpeg_height'), int)
        assert body.get('jpeg_width') >= 0
        assert body.get('jpeg_height') >= 0
        words = body.get('words')
        assert isinstance(words, list)
        assert len(words) == 2

    def test_word_fields_correct(self, client, flask_app):
        """GET /alto/scan_003 → first word has all fields correct; second word has confidence=None."""
        from pathlib import Path

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)

        _write_alto(
            alto_dir / 'scan_003.xml',
            page_w=5146,
            page_h=7548,
            strings=[
                {'CONTENT': 'Hallo', 'HPOS': '100', 'VPOS': '200', 'WIDTH': '80', 'HEIGHT': '30', 'WC': '0.95'},
                {'CONTENT': 'Welt', 'HPOS': '200', 'VPOS': '200', 'WIDTH': '60', 'HEIGHT': '30'},
            ],
        )

        resp = client.get('/alto/scan_003')
        assert resp.status_code == 200
        words = resp.get_json()['words']

        w0 = words[0]
        assert w0['id'] == 'w0'
        assert w0['content'] == 'Hallo'
        assert w0['hpos'] == 100
        assert w0['vpos'] == 200
        assert w0['width'] == 80
        assert w0['height'] == 30
        assert abs(w0['confidence'] - 0.95) < 1e-6

        w1 = words[1]
        assert w1['id'] == 'w1'
        assert w1['content'] == 'Welt'
        # Words with no WC attribute must have confidence=None (not 0, not absent)
        assert w1.get('confidence') is None, (
            f"Expected confidence=None for word without WC, got {w1.get('confidence')!r}"
        )

    def test_jpeg_dims_from_cache(self, client, flask_app):
        """GET /alto/scan_003 → jpeg_width=4, jpeg_height=8 when jpegcache/scan_003.jpg is 4x8."""
        from pathlib import Path
        from PIL import Image
        import io as _io

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        jpegcache_dir = output_dir / 'jpegcache'
        alto_dir.mkdir(parents=True, exist_ok=True)
        jpegcache_dir.mkdir(parents=True, exist_ok=True)

        _write_alto(
            alto_dir / 'scan_003.xml',
            page_w=5146,
            page_h=7548,
            strings=[
                {'CONTENT': 'Hallo', 'HPOS': '100', 'VPOS': '200', 'WIDTH': '80', 'HEIGHT': '30', 'WC': '0.95'},
                {'CONTENT': 'Welt', 'HPOS': '200', 'VPOS': '200', 'WIDTH': '60', 'HEIGHT': '30'},
            ],
        )

        # Write a 4x8 JPEG to jpegcache
        img = Image.new('RGB', (4, 8), color=(200, 100, 50))
        buf = _io.BytesIO()
        img.save(buf, format='JPEG')
        (jpegcache_dir / 'scan_003.jpg').write_bytes(buf.getvalue())

        resp = client.get('/alto/scan_003')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['jpeg_width'] == 4
        assert body['jpeg_height'] == 8

    def test_jpeg_dims_computed_from_tiff_when_cache_absent(self, client, flask_app):
        """GET /alto/scan_004 → jpeg_width=4, jpeg_height=8 computed from TIFF when no cache entry.

        TIFF is 4x8 pixels; max(4,8)=8 < 1600, so no scaling is applied.
        The endpoint reads TIFF dimensions to compute jpeg_width/jpeg_height.
        """
        from pathlib import Path

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        uploads_dir = output_dir / 'uploads'
        alto_dir.mkdir(parents=True, exist_ok=True)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        _write_tiff(uploads_dir / 'scan_004.tif', w=4, h=8)
        _write_alto(
            alto_dir / 'scan_004.xml',
            page_w=800,
            page_h=1200,
            strings=[
                {'CONTENT': 'Test', 'HPOS': '50', 'VPOS': '100', 'WIDTH': '40', 'HEIGHT': '20'},
            ],
        )

        # No jpegcache entry for scan_004
        resp = client.get('/alto/scan_004')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['jpeg_width'] == 4
        assert body['jpeg_height'] == 8

    def test_malformed_xml_returns_500(self, client, flask_app):
        """GET /alto/corrupt → 500, JSON body has 'error' key."""
        from pathlib import Path

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)

        (alto_dir / 'corrupt.xml').write_bytes(b'not xml at all')

        resp = client.get('/alto/corrupt')
        assert resp.status_code == 500
        body = resp.get_json()
        assert body is not None
        assert 'error' in body


# ---------------------------------------------------------------------------
# Phase 11: GET /files endpoint (VIEW-01)
# ---------------------------------------------------------------------------

class TestFilesEndpoint:

    def test_returns_sorted_stems(self, client, flask_app):
        """GET /files: returns stems in alphabetical order."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        (alto_dir / 'scan_002.xml').write_text('<ALTO/>')
        (alto_dir / 'scan_001.xml').write_text('<ALTO/>')
        (alto_dir / 'scan_003.xml').write_text('<ALTO/>')

        resp = client.get('/files')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body is not None
        assert body['stems'] == ['scan_001', 'scan_002', 'scan_003']

    def test_returns_empty_when_no_alto_dir(self, client, flask_app):
        """GET /files: returns {'stems': []} when alto/ does not exist."""
        resp = client.get('/files')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body is not None
        assert body['stems'] == []

    def test_returns_empty_when_alto_dir_empty(self, client, flask_app):
        """GET /files: returns {'stems': []} when alto/ directory has no .xml files."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)

        resp = client.get('/files')
        assert resp.status_code == 200
        assert resp.get_json()['stems'] == []

    def test_ignores_non_xml_files(self, client, flask_app):
        """GET /files: non-.xml files in alto/ are excluded from the stem list."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        (alto_dir / 'scan_001.xml').write_text('<ALTO/>')
        (alto_dir / 'README.txt').write_text('not xml')
        (alto_dir / 'scan_002.json').write_text('{}')

        resp = client.get('/files')
        assert resp.status_code == 200
        assert resp.get_json()['stems'] == ['scan_001']


# ---------------------------------------------------------------------------
# Phase 11: GET / viewer route (VIEW-01 entry point)
# ---------------------------------------------------------------------------

class TestViewerRoute:

    def test_viewer_returns_200_html(self, client, flask_app):
        """GET /: returns 200 with content-type text/html."""
        resp = client.get('/')
        assert resp.status_code == 200
        assert 'text/html' in resp.content_type

    def test_viewer_response_not_empty(self, client, flask_app):
        """GET /: response body is not empty (template loaded successfully)."""
        resp = client.get('/')
        assert len(resp.data) > 0


# ---------------------------------------------------------------------------
# Phase 12: POST /save/<stem> — word correction endpoint (EDIT-02, EDIT-03)
# ---------------------------------------------------------------------------

class TestSaveEndpoint:
    """Tests for POST /save/<stem> endpoint (Plan 12-01)."""

    def _write_alto_fixture(self, path, page_w=5146, page_h=7548, strings=None):
        """Write a minimal ALTO 2.1 XML fixture using lxml etree."""
        from lxml import etree
        ns = ALTO_NS
        if strings is None:
            strings = [
                {'CONTENT': 'Zeitschrift', 'HPOS': '100', 'VPOS': '200', 'WIDTH': '80', 'HEIGHT': '30', 'WC': '0.95'},
                {'CONTENT': 'Berichtigung', 'HPOS': '200', 'VPOS': '200', 'WIDTH': '100', 'HEIGHT': '30'},
            ]
        root = etree.Element(f'{{{ns}}}alto')
        layout = etree.SubElement(root, f'{{{ns}}}Layout')
        page = etree.SubElement(layout, f'{{{ns}}}Page')
        page.set('WIDTH', str(page_w))
        page.set('HEIGHT', str(page_h))
        block = etree.SubElement(page, f'{{{ns}}}PrintSpace')
        tb = etree.SubElement(block, f'{{{ns}}}TextBlock')
        line = etree.SubElement(tb, f'{{{ns}}}TextLine')
        for s in strings:
            elem = etree.SubElement(line, f'{{{ns}}}String')
            for k, v in s.items():
                elem.set(k, str(v))
        path.write_bytes(etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def test_save_updates_alto_on_disk(self, client, flask_app, tmp_path):
        """POST /save/scan_001 with valid word_id and content updates CONTENT on disk."""
        from lxml import etree

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        resp = client.post(
            '/save/scan_001',
            json={'word_id': 'w0', 'content': 'Berichtigung'},
        )
        assert resp.status_code == 200

        # Parse the updated file and verify CONTENT changed
        ns = ALTO_NS
        root = etree.parse(str(alto_dir / 'scan_001.xml')).getroot()
        strings = list(root.iter(f'{{{ns}}}String'))
        assert strings[0].get('CONTENT') == 'Berichtigung', (
            f"Expected 'Berichtigung', got {strings[0].get('CONTENT')!r}"
        )

    def test_save_returns_ok_status(self, client, flask_app, tmp_path):
        """POST /save/scan_001 with valid word_id and content returns {"status": "ok"}."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        resp = client.post(
            '/save/scan_001',
            json={'word_id': 'w0', 'content': 'Berichtigung'},
        )
        assert resp.status_code == 200
        assert resp.get_json() == {'status': 'ok'}

    def test_save_empty_content_returns_422(self, client, flask_app, tmp_path):
        """POST /save/scan_001 with empty content returns 422 without modifying the ALTO file."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        original_content = (alto_dir / 'scan_001.xml').read_bytes()

        resp = client.post(
            '/save/scan_001',
            json={'word_id': 'w0', 'content': ''},
        )
        assert resp.status_code == 422
        # File must be unchanged
        assert (alto_dir / 'scan_001.xml').read_bytes() == original_content

    def test_save_whitespace_only_content_returns_422(self, client, flask_app, tmp_path):
        """POST /save/scan_001 with whitespace-only content returns 422."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        original_content = (alto_dir / 'scan_001.xml').read_bytes()

        resp = client.post(
            '/save/scan_001',
            json={'word_id': 'w0', 'content': '   '},
        )
        assert resp.status_code == 422
        assert (alto_dir / 'scan_001.xml').read_bytes() == original_content

    def test_save_missing_word_id_returns_400(self, client, flask_app, tmp_path):
        """POST /save/scan_001 without word_id returns 400."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        resp = client.post(
            '/save/scan_001',
            json={'content': 'Berichtigung'},
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body is not None
        assert 'word_id' in body.get('error', '')

    def test_save_missing_content_returns_400(self, client, flask_app, tmp_path):
        """POST /save/scan_001 without content returns 400."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        resp = client.post(
            '/save/scan_001',
            json={'word_id': 'w0'},
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body is not None
        assert 'content' in body.get('error', '')

    def test_save_stem_not_found_returns_404(self, client, flask_app, tmp_path):
        """POST /save/nosuchfile returns 404 when no ALTO file exists for stem."""
        resp = client.post(
            '/save/nosuchfile',
            json={'word_id': 'w0', 'content': 'x'},
        )
        assert resp.status_code == 404
        body = resp.get_json()
        assert body is not None
        assert body.get('error') == 'not found'
        assert body.get('stem') == 'nosuchfile'

    def test_save_word_id_out_of_range_returns_404(self, client, flask_app, tmp_path):
        """POST /save/scan_001 with out-of-range word_id returns 404."""
        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        resp = client.post(
            '/save/scan_001',
            json={'word_id': 'w9999', 'content': 'x'},
        )
        assert resp.status_code == 404
        body = resp.get_json()
        assert body is not None
        assert body.get('error') == 'word not found'

    def test_save_atomic_write_on_xsd_failure(self, client, flask_app, tmp_path, monkeypatch):
        """POST /save with content that fails XSD: returns 422, original file unchanged."""
        import app as app_module
        from lxml import etree as _etree

        output_dir = Path(flask_app.config['OUTPUT_DIR'])
        alto_dir = output_dir / 'alto'
        alto_dir.mkdir(parents=True, exist_ok=True)
        self._write_alto_fixture(alto_dir / 'scan_001.xml')

        original_content = (alto_dir / 'scan_001.xml').read_bytes()

        # Build a fake XSD object whose validate() always returns False
        class _FailingSchema:
            def validate(self, doc):
                return False

        monkeypatch.setattr(app_module.pipeline, 'load_xsd', lambda path: _FailingSchema())

        resp = client.post(
            '/save/scan_001',
            json={'word_id': 'w0', 'content': 'ValidContent'},
        )
        assert resp.status_code == 422
        assert (alto_dir / 'scan_001.xml').read_bytes() == original_content
