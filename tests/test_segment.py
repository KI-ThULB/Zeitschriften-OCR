"""Tests for vlm.py provider module and POST/GET /segment/<stem> endpoints."""
import json
import importlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import vlm


# ---------------------------------------------------------------------------
# vlm.get_provider factory
# ---------------------------------------------------------------------------

class TestGetProvider:

    def test_returns_claude_provider(self):
        p = vlm.get_provider('claude', 'claude-opus-4-6', 'key')
        assert isinstance(p, vlm.ClaudeProvider)

    def test_returns_openai_provider(self):
        p = vlm.get_provider('openai', 'gpt-4o', 'key')
        assert isinstance(p, vlm.OpenAIProvider)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match='Unknown VLM provider'):
            vlm.get_provider('gemini', 'gemini-pro', 'key')


# ---------------------------------------------------------------------------
# vlm._parse_regions
# ---------------------------------------------------------------------------

class TestParseRegions:

    def test_valid_single_region(self):
        text = '{"regions": [{"type": "article", "title": "Test Article", "bounding_box": {"x": 0.0, "y": 0.1, "width": 0.5, "height": 0.3}}]}'
        regions = vlm._parse_regions(text)
        assert len(regions) == 1
        assert regions[0]['id'] == 'r0'
        assert regions[0]['type'] == 'article'
        assert regions[0]['title'] == 'Test Article'
        assert regions[0]['bounding_box']['x'] == 0.0

    def test_empty_regions_list(self):
        regions = vlm._parse_regions('{"regions": []}')
        assert regions == []

    def test_invalid_json_returns_empty(self):
        regions = vlm._parse_regions('not json at all')
        assert regions == []

    def test_json_with_preamble(self):
        text = 'Sure! Here is the analysis:\n{"regions": [{"type": "headline", "title": "Big News", "bounding_box": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.1}}]}'
        regions = vlm._parse_regions(text)
        assert len(regions) == 1
        assert regions[0]['type'] == 'headline'

    def test_invalid_type_filtered_out(self):
        text = '{"regions": [{"type": "unknown_type", "title": "X", "bounding_box": {"x": 0, "y": 0, "width": 1, "height": 1}}]}'
        regions = vlm._parse_regions(text)
        assert regions == []

    def test_all_valid_types_accepted(self):
        for rtype in ('headline', 'article', 'advertisement', 'illustration', 'caption'):
            text = f'{{"regions": [{{"type": "{rtype}", "title": "T", "bounding_box": {{"x": 0, "y": 0, "width": 1, "height": 1}}}}]}}'
            regions = vlm._parse_regions(text)
            assert len(regions) == 1, f'Expected 1 region for type {rtype}'

    def test_multiple_regions_get_sequential_ids(self):
        text = '{"regions": [{"type": "headline", "title": "A", "bounding_box": {"x": 0, "y": 0, "width": 1, "height": 0.1}}, {"type": "article", "title": "B", "bounding_box": {"x": 0, "y": 0.1, "width": 1, "height": 0.5}}]}'
        regions = vlm._parse_regions(text)
        assert len(regions) == 2
        assert regions[0]['id'] == 'r0'
        assert regions[1]['id'] == 'r1'

    def test_missing_bounding_box_filtered_out(self):
        text = '{"regions": [{"type": "article", "title": "X"}]}'
        regions = vlm._parse_regions(text)
        assert regions == []


# ---------------------------------------------------------------------------
# POST /segment/<stem>
# ---------------------------------------------------------------------------

class TestSegmentPost:

    def _setup_jpeg(self, tmp_path, stem='page001'):
        cache_dir = tmp_path / 'segcache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        jpeg_path = cache_dir / f'{stem}.jpg'
        jpeg_path.write_bytes(b'FAKEJPEG')
        return jpeg_path

    def test_success_returns_regions_and_writes_json(self, client, flask_app, tmp_path, monkeypatch):
        import app as app_module
        self._setup_jpeg(tmp_path)

        flask_app.config['VLM_PROVIDER'] = 'claude'
        flask_app.config['VLM_MODEL'] = 'claude-opus-4-6'
        flask_app.config['VLM_API_KEY'] = 'test-key'

        mock_regions = [{'id': 'r0', 'type': 'article', 'title': 'Test', 'bounding_box': {'x': 0, 'y': 0, 'width': 1, 'height': 1}}]
        mock_provider = MagicMock()
        mock_provider.segment.return_value = mock_regions
        monkeypatch.setattr(app_module.vlm, 'get_provider', lambda *a: mock_provider)

        resp = client.post('/segment/page001')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['stem'] == 'page001'
        assert data['regions'] == mock_regions

        seg_file = tmp_path / 'segments' / 'page001.json'
        assert seg_file.exists()
        stored = json.loads(seg_file.read_text())
        assert stored['stem'] == 'page001'
        assert stored['provider'] == 'claude'
        assert stored['model'] == 'claude-opus-4-6'
        assert 'segmented_at' in stored
        assert stored['regions'] == mock_regions

    def test_no_provider_configured_returns_503(self, client, flask_app):
        flask_app.config.pop('VLM_PROVIDER', None)
        resp = client.post('/segment/page001')
        assert resp.status_code == 503
        assert 'provider' in resp.get_json().get('error', '').lower()

    def test_jpeg_not_in_cache_returns_404(self, client, flask_app):
        flask_app.config['VLM_PROVIDER'] = 'claude'
        flask_app.config['VLM_MODEL'] = 'claude-opus-4-6'
        flask_app.config['VLM_API_KEY'] = 'key'
        resp = client.post('/segment/nonexistent')
        assert resp.status_code == 404

    def test_provider_api_error_returns_502(self, client, flask_app, tmp_path, monkeypatch):
        import app as app_module
        self._setup_jpeg(tmp_path)
        flask_app.config['VLM_PROVIDER'] = 'claude'
        flask_app.config['VLM_MODEL'] = 'claude-opus-4-6'
        flask_app.config['VLM_API_KEY'] = 'key'
        mock_provider = MagicMock()
        mock_provider.segment.side_effect = RuntimeError('API error')
        monkeypatch.setattr(app_module.vlm, 'get_provider', lambda *a: mock_provider)

        resp = client.post('/segment/page001')
        assert resp.status_code == 502
        assert 'error' in resp.get_json()

    def test_empty_regions_stored_correctly(self, client, flask_app, tmp_path, monkeypatch):
        import app as app_module
        self._setup_jpeg(tmp_path)
        flask_app.config['VLM_PROVIDER'] = 'claude'
        flask_app.config['VLM_MODEL'] = 'claude-opus-4-6'
        flask_app.config['VLM_API_KEY'] = 'key'
        mock_provider = MagicMock()
        mock_provider.segment.return_value = []
        monkeypatch.setattr(app_module.vlm, 'get_provider', lambda *a: mock_provider)

        resp = client.post('/segment/page001')
        assert resp.status_code == 200
        assert resp.get_json()['regions'] == []

        seg_file = tmp_path / 'segments' / 'page001.json'
        stored = json.loads(seg_file.read_text())
        assert stored['regions'] == []

    def test_path_traversal_returns_400(self, client):
        resp = client.post('/segment/bad..stem')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /segment/<stem>
# ---------------------------------------------------------------------------

class TestSegmentGet:

    def test_returns_stored_json(self, client, flask_app, tmp_path):
        seg_dir = tmp_path / 'segments'
        seg_dir.mkdir(parents=True, exist_ok=True)
        stored = {
            'stem': 'page001', 'provider': 'claude', 'model': 'claude-opus-4-6',
            'segmented_at': '2026-03-01T00:00:00',
            'regions': [{'id': 'r0', 'type': 'article', 'title': 'T', 'bounding_box': {'x': 0, 'y': 0, 'width': 1, 'height': 1}}],
        }
        (seg_dir / 'page001.json').write_text(json.dumps(stored))

        resp = client.get('/segment/page001')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['stem'] == 'page001'
        assert len(data['regions']) == 1

    def test_not_yet_segmented_returns_404(self, client, flask_app):
        resp = client.get('/segment/nosuchstem')
        assert resp.status_code == 404

    def test_path_traversal_returns_400(self, client):
        resp = client.get('/segment/bad..stem')
        assert resp.status_code == 400
