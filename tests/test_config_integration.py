"""Integration tests for --config flag wiring in main().

Covers the CLI integration layer: two-pass argparse, set_defaults() precedence,
and verbose config summary. These tests differ from tests/test_load_config.py,
which only tests load_config() in isolation.

Tests:
  1. Config sets default lang (set_defaults injection works)
  2. CLI flag overrides config value (CLI wins)
  3. No --config leaves defaults unchanged (no-op)
  4. Verbose config summary printed with override notation
  5. Verbose config summary suppressed without --verbose
  6. Unknown key warning always shown regardless of --verbose
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stubs():
    """Return a dict of attribute names -> no-op MagicMock stubs for heavy functions.

    Used with patch.multiple('pipeline', **stubs), so keys are bare attribute names.
    """
    return {
        'validate_tesseract': MagicMock(return_value=None),
        'discover_tiffs': MagicMock(return_value=[]),
        'run_batch': MagicMock(return_value=(0, 0, [], [])),
        'write_error_log': MagicMock(return_value=None),
        'load_xsd': MagicMock(return_value=None),
        'validate_batch': MagicMock(return_value=([], 0)),
        'write_report': MagicMock(return_value=Path('/tmp/report.json')),
    }


def _run_main_with_argv(argv, stubs, tmp_path):
    """Run pipeline.main() with the given argv and stubs, returning (exit_code, stdout, stderr).

    Creates a real input directory and output directory under tmp_path to satisfy
    the --input is_dir() check inside main(). Uses capsys indirectly via direct
    call rather than subprocess, so callers must use capsys themselves.
    """
    input_dir = tmp_path / 'input'
    input_dir.mkdir()
    output_dir = tmp_path / 'output'
    output_dir.mkdir()

    full_argv = ['pipeline.py'] + argv + [
        '--input', str(input_dir),
        '--output', str(output_dir),
    ]

    exit_code = 0
    with patch.multiple('pipeline', **stubs):
        with patch.object(sys, 'argv', full_argv):
            try:
                pipeline.main()
            except SystemExit as e:
                exit_code = e.code if e.code is not None else 0

    return exit_code


# ---------------------------------------------------------------------------
# Test 1: Config sets default lang
# ---------------------------------------------------------------------------

def test_config_sets_default_lang(tmp_path, capsys):
    """Config {"lang": "eng"} causes validate_tesseract to be called with "eng"."""
    cfg = tmp_path / 'myconfig.json'
    cfg.write_text(json.dumps({'lang': 'eng'}))

    stubs = _make_stubs()
    _run_main_with_argv(['--config', str(cfg)], stubs, tmp_path)

    # validate_tesseract should have been called with "eng" (from config), not "deu" (default)
    stubs['validate_tesseract'].assert_called_once_with('eng')


# ---------------------------------------------------------------------------
# Test 2: CLI overrides config
# ---------------------------------------------------------------------------

def test_cli_overrides_config(tmp_path, capsys):
    """CLI --lang deu wins over config {"lang": "fra"}."""
    cfg = tmp_path / 'myconfig.json'
    cfg.write_text(json.dumps({'lang': 'fra'}))

    stubs = _make_stubs()
    _run_main_with_argv(['--config', str(cfg), '--lang', 'deu'], stubs, tmp_path)

    # CLI passed --lang deu, config had fra — validate_tesseract must receive deu
    stubs['validate_tesseract'].assert_called_once_with('deu')


# ---------------------------------------------------------------------------
# Test 3: No --config leaves defaults unchanged
# ---------------------------------------------------------------------------

def test_no_config_unchanged_defaults(tmp_path, capsys):
    """Without --config, args.lang defaults to 'deu' (original add_argument default)."""
    stubs = _make_stubs()
    _run_main_with_argv([], stubs, tmp_path)

    # Should use the original 'deu' default from add_argument()
    stubs['validate_tesseract'].assert_called_once_with('deu')


# ---------------------------------------------------------------------------
# Test 4: Verbose config summary printed with override notation
# ---------------------------------------------------------------------------

def test_verbose_config_summary_printed(tmp_path, capsys):
    """With --verbose --config and CLI override, Config: summary line appears on stdout."""
    cfg = tmp_path / 'myconfig.json'
    cfg.write_text(json.dumps({'lang': 'eng'}))

    stubs = _make_stubs()
    _run_main_with_argv(
        ['--config', str(cfg), '--verbose', '--lang', 'deu'],
        stubs,
        tmp_path,
    )

    captured = capsys.readouterr()
    # Config had lang=eng, CLI passed --lang deu — summary must show override
    assert 'Config:' in captured.out
    assert 'lang=eng' in captured.out
    assert 'deu (CLI override)' in captured.out
    assert f'(from {cfg.name})' in captured.out


# ---------------------------------------------------------------------------
# Test 5: Verbose config summary suppressed without --verbose
# ---------------------------------------------------------------------------

def test_verbose_config_summary_suppressed_without_verbose(tmp_path, capsys):
    """Without --verbose, no Config: summary line appears even with a config file."""
    cfg = tmp_path / 'myconfig.json'
    cfg.write_text(json.dumps({'lang': 'eng'}))

    stubs = _make_stubs()
    _run_main_with_argv(['--config', str(cfg)], stubs, tmp_path)

    captured = capsys.readouterr()
    assert 'Config:' not in captured.out


# ---------------------------------------------------------------------------
# Test 6: Unknown key warning always shown regardless of --verbose
# ---------------------------------------------------------------------------

def test_unknown_key_warning_always_shown(tmp_path, capsys):
    """[WARN: unknown config key 'X'] appears on stderr even without --verbose."""
    cfg = tmp_path / 'myconfig.json'
    cfg.write_text(json.dumps({'lang': 'deu', 'unknown_key': 'x'}))

    stubs = _make_stubs()
    _run_main_with_argv(['--config', str(cfg)], stubs, tmp_path)

    captured = capsys.readouterr()
    assert "[WARN: unknown config key 'unknown_key']" in captured.err
