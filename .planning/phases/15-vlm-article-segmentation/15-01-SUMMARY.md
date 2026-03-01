---
phase: 15-vlm-article-segmentation
plan: "01"
subsystem: vlm-segmentation
tags: [vlm, flask, claude, openai, segmentation, tdd]
dependency_graph:
  requires: []
  provides: [vlm-module, segment-endpoints]
  affects: [app.py, requirements.txt]
tech_stack:
  added: [anthropic>=0.40.0, openai>=1.0.0]
  patterns: [provider-abstraction, lazy-import, tdd-red-green, json-response-parsing]
key_files:
  created:
    - vlm.py
    - tests/test_segment.py
  modified:
    - app.py
    - requirements.txt
decisions:
  - Lazy SDK imports inside segment() methods so vlm.py loads without anthropic/openai installed
  - _parse_regions uses re.search for JSON extraction to handle VLM preamble/postamble
  - Provider error handling in POST /segment: any Exception from provider.segment() -> 502
  - API key resolution order: VLM_API_KEY config > ANTHROPIC_API_KEY > OPENAI_API_KEY env vars
metrics:
  duration: "3m 27s"
  completed: "2026-03-01"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 2
  tests_added: 20
  tests_final: 79
---

# Phase 15 Plan 01: VLM Article Segmentation — Backend Summary

**One-liner:** Provider-agnostic VLM segmentation backend with ClaudeProvider/OpenAIProvider abstraction, JSON region parser, and POST/GET /segment/<stem> Flask endpoints storing normalized bounding-box regions per page.

## What Was Built

### vlm.py (new)

Full provider abstraction module at project root:

- `SegmentationProvider` — abstract base class with `segment(jpeg_path)` interface
- `ClaudeProvider` — calls `anthropic.Anthropic().messages.create()` with base64 JPEG and `SEGMENT_PROMPT`; anthropic SDK lazy-imported
- `OpenAIProvider` — calls `openai.OpenAI().chat.completions.create()` with base64 data URL; openai SDK lazy-imported
- `get_provider(name, model, api_key)` — factory returning the correct provider; raises `ValueError` for unknown names
- `_parse_regions(text)` — extracts JSON from VLM response (handles preamble via `re.search`), filters by `VALID_TYPES`, assigns sequential `r{N}` IDs, returns `[]` on any failure (never raises)
- `SEGMENT_PROMPT` — structured prompt requesting normalized bounding box regions (0.0–1.0 fractions)
- `VALID_TYPES` — frozenset of `{headline, article, advertisement, illustration, caption}`

### app.py (modified)

- Added `import vlm` alongside `import pipeline`
- `POST /segment/<stem>` — reads `output/jpegcache/<stem>.jpg`, calls `vlm.get_provider()`, writes `output/segments/<stem>.json`, returns full result dict
  - 400: path traversal in stem
  - 503: VLM_PROVIDER not configured
  - 404: JPEG not in jpegcache
  - 502: any exception from provider.segment()
  - 200: success with `{stem, provider, model, segmented_at, regions}`
- `GET /segment/<stem>` — returns stored JSON from `output/segments/<stem>.json`; 404 if absent
- CLI flags: `--vlm-provider`, `--vlm-model`, `--vlm-api-key` wired into `app.config`

### requirements.txt (modified)

Added `anthropic>=0.40.0` and `openai>=1.0.0`.

### tests/test_segment.py (new, TDD)

20 tests across 4 classes:
- `TestGetProvider` (3 tests): factory returns correct types, raises ValueError for unknown
- `TestParseRegions` (8 tests): valid region, empty list, invalid JSON, preamble, invalid type, all valid types, sequential IDs, missing bounding_box
- `TestSegmentPost` (6 tests): success+file written, 503 no provider, 404 JPEG missing, 502 API error, empty regions stored, path traversal 400
- `TestSegmentGet` (3 tests): stored JSON returned, 404 not segmented, path traversal 400

## Test Results

```
79 passed in 1.22s
```

All 79 tests pass (20 new + 59 pre-existing, no regressions).

## Commits

| Hash    | Message |
|---------|---------|
| 74e8532 | test(15-01): add failing tests for vlm module and segment endpoints |
| f080451 | feat(15-01): create vlm.py provider abstraction module |
| 774a467 | feat(15-01): add POST/GET /segment/<stem> routes and VLM CLI flags to app.py |

## Deviations from Plan

None — plan executed exactly as written.

## Requirements Satisfied

- STRUCT-01: VLM provider configurable via `--vlm-provider`/`--vlm-model` CLI flags; env var fallback for API key
- STRUCT-02: Detected regions have bounding_box, type, title; stored in `output/segments/<stem>.json`
- STRUCT-03: Each region has title and type as structured metadata fields extracted from VLM response

## Self-Check: PASSED

Files created:
- vlm.py: FOUND
- tests/test_segment.py: FOUND

Commits verified:
- 74e8532: FOUND
- f080451: FOUND
- 774a467: FOUND
