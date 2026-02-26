"""Tests for load_config() — JSON config file validator.

Covers:
  - Valid config returns dict with correct values
  - Empty config returns {}
  - Unknown key warns to stderr but returns dict without unknown key
  - Mix of known and unknown keys
  - Missing file exits with code 1 and correct message
  - Invalid JSON exits with code 1 and correct message
  - Type error (str for int key) exits with code 1 and correct message
  - bool for int key exits with code 1 and correct message (bool is subclass of int)
  - Wrong type for str key exits with code 1 and correct message
  - Wrong type for bool key (e.g. int) exits with code 1 and correct message
"""
import json
import sys
from pathlib import Path

import pytest

from pipeline import load_config


# ---------------------------------------------------------------------------
# PASS cases
# ---------------------------------------------------------------------------

def test_valid_all_known_keys(tmp_path):
    """Valid JSON with all known keys returns a clean validated dict."""
    config = {
        "lang": "deu",
        "psm": 3,
        "padding": 100,
        "workers": 2,
        "force": True,
        "verbose": False,
        "dry_run": False,
        "validate_only": False,
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    result = load_config(cfg_file)
    assert result == config


def test_empty_config_returns_empty_dict(tmp_path):
    """Empty JSON object returns {}."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("{}")
    result = load_config(cfg_file)
    assert result == {}


def test_unknown_key_warns_and_is_excluded(tmp_path, capsys):
    """Unknown key emits [WARN: unknown config key 'X'] to stderr and is excluded from result."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"lang": "eng", "typo_key": "oops"}))
    result = load_config(cfg_file)
    assert "typo_key" not in result
    assert result == {"lang": "eng"}
    captured = capsys.readouterr()
    assert "[WARN: unknown config key 'typo_key']" in captured.err


def test_mix_known_and_unknown_keys(tmp_path, capsys):
    """Mix of known and unknown keys: only known are returned; each unknown warns."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"workers": 4, "foo": 1, "bar": "baz"}))
    result = load_config(cfg_file)
    assert result == {"workers": 4}
    captured = capsys.readouterr()
    assert "[WARN: unknown config key 'foo']" in captured.err
    assert "[WARN: unknown config key 'bar']" in captured.err


def test_partial_known_keys(tmp_path):
    """Config with only a subset of known keys returns only those keys."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"lang": "eng", "padding": 75}))
    result = load_config(cfg_file)
    assert result == {"lang": "eng", "padding": 75}


# ---------------------------------------------------------------------------
# EXIT 1 cases
# ---------------------------------------------------------------------------

def test_missing_file_exits(tmp_path, capsys):
    """Missing config file prints 'Error: config file not found:' and exits with code 1."""
    missing = tmp_path / "nonexistent.json"
    with pytest.raises(SystemExit) as exc_info:
        load_config(missing)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config file not found:" in captured.err
    assert str(missing) in captured.err


def test_invalid_json_exits(tmp_path, capsys):
    """Invalid JSON prints 'Error: config file contains invalid JSON:' and exits with code 1."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("{not valid json")
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config file contains invalid JSON:" in captured.err


def test_type_error_str_for_int_exits(tmp_path, capsys):
    """workers='four' (str for int) exits with code 1 naming key and expected type."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"workers": "four"}))
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config key 'workers' expects int, got str" in captured.err


def test_bool_for_int_key_exits(tmp_path, capsys):
    """workers=true (JSON bool, Python bool) rejected for int-typed key — bool is subclass of int."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"workers": True}))
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config key 'workers' expects int, got bool" in captured.err


def test_bool_for_int_key_psm(tmp_path, capsys):
    """psm=false (JSON bool) rejected for int-typed key 'psm'."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"psm": False}))
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config key 'psm' expects int, got bool" in captured.err


def test_type_error_int_for_str_exits(tmp_path, capsys):
    """lang=42 (int for str) exits with code 1 naming key and expected type."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"lang": 42}))
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config key 'lang' expects str, got int" in captured.err


def test_type_error_str_for_bool_exits(tmp_path, capsys):
    """force='yes' (str for bool) exits with code 1 naming key and expected type."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"force": "yes"}))
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config key 'force' expects bool, got str" in captured.err


def test_type_error_int_for_bool_exits(tmp_path, capsys):
    """verbose=1 (int for bool) exits with code 1 — int is not bool."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"verbose": 1}))
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config key 'verbose' expects bool, got int" in captured.err


def test_type_error_exits_on_first_bad_key(tmp_path, capsys):
    """When multiple keys are wrong, exits on the first type error encountered."""
    cfg_file = tmp_path / "config.json"
    # workers is invalid — should exit before reaching padding
    cfg_file.write_text(json.dumps({"workers": "bad", "padding": "also_bad"}))
    with pytest.raises(SystemExit) as exc_info:
        load_config(cfg_file)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: config key 'workers' expects int, got str" in captured.err


def test_error_prefix_is_capital_e_lowercase_r(tmp_path, capsys):
    """Error messages use 'Error:' (capital E, lower r) — not 'ERROR:' as in validate_tesseract()."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"workers": "bad"}))
    with pytest.raises(SystemExit):
        load_config(cfg_file)
    captured = capsys.readouterr()
    # Must contain 'Error:' not 'ERROR:'
    assert "Error:" in captured.err
    assert "ERROR:" not in captured.err
