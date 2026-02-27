"""Tests for app.py — Phase 9: Flask Foundation and Job State.

PROC-03: Already-processed TIFFs are skipped automatically.
PROC-04: Per-file OCR errors are reported without stopping the batch.
"""
import json
import queue
import io
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
