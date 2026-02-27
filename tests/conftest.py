# --- Phase 9: Flask app fixtures ---
import pytest


@pytest.fixture()
def flask_app(tmp_path):
    """Flask test app with isolated temp output directory."""
    import importlib
    app_module = importlib.import_module('app')
    application = app_module.app
    application.config.update({
        'TESTING': True,
        'OUTPUT_DIR': str(tmp_path),
    })
    # Reset module-level state between tests
    app_module._jobs.clear()
    app_module._run_active.clear()
    yield application


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()
