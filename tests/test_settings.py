"""Tests for VLM settings persistence: OpenAICompatibleProvider, GET/POST /settings,
GET /settings/models, and segment_page() settings.json read path."""
import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import vlm


# ---------------------------------------------------------------------------
# vlm.py — OpenAICompatibleProvider
# ---------------------------------------------------------------------------

class TestOpenAICompatibleProvider:

    def test_openai_compatible_provider_exists(self):
        """OpenAICompatibleProvider class importable from vlm."""
        from vlm import OpenAICompatibleProvider
        assert OpenAICompatibleProvider is not None

    def test_get_provider_openai_compatible(self):
        """get_provider('openai_compatible', model, key, base_url=...) returns OpenAICompatibleProvider."""
        from vlm import OpenAICompatibleProvider
        p = vlm.get_provider('openai_compatible', 'llama3.2-vision', 'test-key',
                              base_url='https://example.com/v1')
        assert isinstance(p, OpenAICompatibleProvider)

    def test_get_provider_unknown_still_raises(self):
        """get_provider raises ValueError for unknown provider names."""
        with pytest.raises(ValueError, match='Unknown VLM provider'):
            vlm.get_provider('unknown', 'model', 'key')

    def test_openai_compatible_segment_calls_openai(self, tmp_path):
        """OpenAICompatibleProvider.segment() calls openai.OpenAI with base_url and api_key."""
        jpeg = tmp_path / 'test.jpg'
        jpeg.write_bytes(b'FAKEJPEG')

        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"regions": []}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls = MagicMock(return_value=mock_client)

        # Patch sys.modules so the lazy import inside segment() gets our mock
        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI = mock_openai_cls
        original = sys.modules.get('openai')
        sys.modules['openai'] = mock_openai_module

        try:
            from vlm import OpenAICompatibleProvider
            p = OpenAICompatibleProvider('llama3.2-vision', 'test-key', 'https://example.com/v1')
            result = p.segment(jpeg)
        finally:
            # Restore original module state
            if original is None:
                sys.modules.pop('openai', None)
            else:
                sys.modules['openai'] = original

        assert result == []
        mock_openai_cls.assert_called_once_with(
            base_url='https://example.com/v1', api_key='test-key'
        )


# ---------------------------------------------------------------------------
# app.py — GET /settings
# ---------------------------------------------------------------------------

class TestGetSettings:

    def test_get_settings_empty(self, client, flask_app, tmp_path):
        """GET /settings returns {} when no settings.json exists."""
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        resp = client.get('/settings')
        assert resp.status_code == 200
        assert resp.get_json() == {}

    def test_get_settings_returns_file(self, client, flask_app, tmp_path):
        """GET /settings returns persisted settings from settings.json."""
        settings = {
            'backend': 'openai_compatible',
            'base_url': 'https://example.com',
            'api_key': 'k',
            'model': 'm',
        }
        (tmp_path / 'settings.json').write_text(json.dumps(settings))
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        resp = client.get('/settings')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['backend'] == 'openai_compatible'
        assert data['model'] == 'm'


# ---------------------------------------------------------------------------
# app.py — POST /settings
# ---------------------------------------------------------------------------

class TestPostSettings:

    def test_post_settings_writes_file(self, client, flask_app, tmp_path):
        """POST /settings writes settings.json and returns 200."""
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        payload = {
            'backend': 'openai_compatible',
            'base_url': 'https://example.com/v1',
            'api_key': 'key123',
            'model': 'llama3.2',
        }
        resp = client.post('/settings', json=payload)
        assert resp.status_code == 200
        saved = json.loads((tmp_path / 'settings.json').read_text())
        assert saved['api_key'] == 'key123'
        assert saved['model'] == 'llama3.2'

    def test_post_settings_missing_backend_returns_400(self, client, flask_app, tmp_path):
        """POST /settings returns 400 if backend field is missing."""
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        resp = client.post('/settings', json={'model': 'x'})
        assert resp.status_code == 400

    def test_post_settings_invalid_backend_returns_400(self, client, flask_app, tmp_path):
        """POST /settings returns 400 if backend is not a known value."""
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        resp = client.post('/settings', json={
            'backend': 'unknown_backend',
            'base_url': 'x',
            'api_key': 'k',
            'model': 'm',
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# app.py — GET /settings/models
# ---------------------------------------------------------------------------

class TestSettingsModels:

    def test_settings_models_missing_params(self, client):
        """GET /settings/models without base_url and api_key returns 400."""
        resp = client.get('/settings/models')
        assert resp.status_code == 400

    def test_settings_models_calls_api(self, client):
        """GET /settings/models fetches /models from base_url using api_key."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock(id='model-a'), MagicMock(id='model-b')]
        mock_client = MagicMock()
        mock_client.models.list.return_value = mock_response
        mock_openai_cls = MagicMock(return_value=mock_client)

        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI = mock_openai_cls
        original = sys.modules.get('openai')
        sys.modules['openai'] = mock_openai_module

        try:
            resp = client.get('/settings/models?base_url=https://example.com/v1&api_key=test-key')
        finally:
            if original is None:
                sys.modules.pop('openai', None)
            else:
                sys.modules['openai'] = original

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'models' in data

    def test_settings_models_api_error_returns_502(self, client):
        """GET /settings/models returns 502 if the remote API errors."""
        mock_openai_cls = MagicMock(side_effect=Exception('connection refused'))
        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI = mock_openai_cls
        original = sys.modules.get('openai')
        sys.modules['openai'] = mock_openai_module

        try:
            resp = client.get('/settings/models?base_url=https://bad.example/v1&api_key=key')
        finally:
            if original is None:
                sys.modules.pop('openai', None)
            else:
                sys.modules['openai'] = original

        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# app.py — segment_page() reads settings.json
# ---------------------------------------------------------------------------

class TestSegmentUsesSettings:

    def _setup_jpeg(self, output_dir: Path, stem: str = 'test') -> None:
        jpeg_dir = output_dir / 'segcache'
        jpeg_dir.mkdir(parents=True, exist_ok=True)
        (jpeg_dir / f'{stem}.jpg').write_bytes(b'FAKEJPEG')

    def test_segment_uses_settings_json(self, client, flask_app, tmp_path):
        """segment_page() uses settings.json provider when app.config has no VLM_PROVIDER."""
        app_module = importlib.import_module('app')
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        flask_app.config['VLM_PROVIDER'] = ''
        self._setup_jpeg(tmp_path)

        # Write settings.json with openai_compatible
        settings = {
            'backend': 'openai_compatible',
            'base_url': 'https://x.com/v1',
            'api_key': 'k',
            'model': 'm',
        }
        (tmp_path / 'settings.json').write_text(json.dumps(settings))

        mock_provider = MagicMock()
        mock_provider.segment.return_value = []

        original_make = getattr(app_module, '_make_provider_from_settings', None)
        app_module._make_provider_from_settings = lambda s: mock_provider

        try:
            resp = client.post('/segment/test')
        finally:
            if original_make is None:
                if hasattr(app_module, '_make_provider_from_settings'):
                    delattr(app_module, '_make_provider_from_settings')
            else:
                app_module._make_provider_from_settings = original_make

        assert resp.status_code == 200
        mock_provider.segment.assert_called_once()

    def test_segment_falls_back_to_config_when_no_settings(self, client, flask_app, tmp_path):
        """segment_page() falls back to app.config VLM_PROVIDER when no settings.json."""
        app_module = importlib.import_module('app')
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        flask_app.config['VLM_PROVIDER'] = 'claude'
        flask_app.config['VLM_MODEL'] = 'claude-opus-4-6'
        flask_app.config['VLM_API_KEY'] = 'test-api-key'
        self._setup_jpeg(tmp_path)

        mock_provider = MagicMock()
        mock_provider.segment.return_value = []

        original_get_provider = app_module.vlm.get_provider
        app_module.vlm.get_provider = lambda *a, **k: mock_provider

        try:
            resp = client.post('/segment/test')
        finally:
            app_module.vlm.get_provider = original_get_provider

        assert resp.status_code == 200

    def test_segment_returns_503_when_no_provider_no_settings(self, client, flask_app, tmp_path):
        """segment_page() returns 503 when no settings.json and no app.config VLM_PROVIDER."""
        flask_app.config['OUTPUT_DIR'] = str(tmp_path)
        flask_app.config['VLM_PROVIDER'] = ''
        self._setup_jpeg(tmp_path)
        resp = client.post('/segment/test')
        assert resp.status_code == 503
