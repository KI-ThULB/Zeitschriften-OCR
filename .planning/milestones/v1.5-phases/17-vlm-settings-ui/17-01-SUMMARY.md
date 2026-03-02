---
phase: 17-vlm-settings-ui
plan: 01
subsystem: api
tags: [flask, vlm, openai, settings, persistence]

# Dependency graph
requires:
  - phase: 15-vlm-article-segmentation
    provides: vlm.py provider abstraction, segment_page() endpoint
  - phase: 16-mets-mods-output
    provides: app.py with GET /mets, 101 passing tests baseline
provides:
  - OpenAICompatibleProvider class in vlm.py (Open WebUI, OpenRouter, Ollama support)
  - GET /settings — returns current output/settings.json or {}
  - POST /settings — validates and atomically writes output/settings.json
  - GET /settings/models — live model list from any OpenAI-compatible endpoint
  - segment_page() reads settings.json first, then falls back to CLI app.config
affects: [17-vlm-settings-ui phase 17-02 frontend]

# Tech tracking
tech-stack:
  added: [openai SDK (lazy import, already available from phase 15)]
  patterns:
    - Atomic write via tempfile.mkstemp + os.replace for settings.json
    - Lazy openai import inside segment() and route handler — no top-level SDK dependency
    - Provider resolution precedence: settings.json > CLI config > 503
    - sys.modules patching in tests for lazy-imported openai module

key-files:
  created:
    - tests/test_settings.py
  modified:
    - vlm.py
    - app.py

key-decisions:
  - "OpenAICompatibleProvider uses lazy import openai inside segment() — consistent with ClaudeProvider/OpenAIProvider pattern"
  - "settings.json lives at output/settings.json (Path(app.config['OUTPUT_DIR']) / 'settings.json')"
  - "Atomic write uses tempfile.mkstemp in same directory + os.replace — same pattern as ALTO XML save"
  - "provider_name/model for result dict resolved in else branch when provider came from settings.json"
  - "sys.modules patching in tests rather than monkeypatch.setattr — handles lazy import inside route/segment()"

patterns-established:
  - "Settings helpers (_load_settings, _save_settings, _make_provider_from_settings) before module constants in app.py"
  - "TDD: 12 tests RED at commit 61c7bf4, then GREEN after implementation at 53da80a"

requirements-completed: [STRUCT-02]

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 17 Plan 01: VLM Settings Persistence Backend Summary

**OpenAICompatibleProvider + GET/POST /settings + GET /settings/models, persisting to output/settings.json with atomic writes, segment_page() reads settings first**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-01T22:36:26Z
- **Completed:** 2026-03-01T22:40:53Z
- **Tasks:** 4
- **Files modified:** 3 (tests/test_settings.py created, vlm.py modified, app.py modified)

## Accomplishments
- OpenAICompatibleProvider in vlm.py with lazy openai import, accepts model/api_key/base_url — covers Open WebUI and OpenRouter
- Three new Flask endpoints: GET /settings (returns settings.json or {}), POST /settings (validates + atomically writes), GET /settings/models (live model list from any OpenAI-compatible /models endpoint)
- segment_page() updated with settings.json read path — operators configure VLM from web UI without CLI flags or server restarts
- 15 new tests, all GREEN; 101 existing tests maintain zero regressions (116 total)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write TDD tests (RED)** - `61c7bf4` (test)
2. **Task 2: Add OpenAICompatibleProvider to vlm.py** - `d11645e` (feat)
3. **Task 3: Add settings helpers and endpoints to app.py** - `53da80a` (feat)
4. **Task 4: Run full test suite GREEN** - (verified at `53da80a`, no additional changes needed)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `tests/test_settings.py` - 15 TDD tests covering OpenAICompatibleProvider, GET/POST /settings, GET /settings/models, segment_page() settings read path
- `vlm.py` - Added OpenAICompatibleProvider class, updated SUPPORTED_PROVIDERS, updated get_provider() with optional base_url kwarg
- `app.py` - Added import contextlib, _VALID_BACKENDS, _load_settings(), _save_settings(), _make_provider_from_settings(), GET /settings, POST /settings, GET /settings/models routes, updated segment_page() provider resolution

## Decisions Made
- Used `sys.modules` patching in tests for the lazy `import openai` inside route handlers and `segment()` — `monkeypatch.setattr` doesn't intercept lazy imports that haven't happened yet
- Fixed `provider_name`/`model` undefined bug in result dict: added `else` branch to set them from settings when provider came from settings.json (Rule 1 auto-fix, found during Task 3)
- `_make_provider_from_settings` returns `None` when backend not in `_VALID_BACKENDS` or model is empty — avoids partial-config provider creation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed NameError: provider_name and model undefined in segment_page() result dict**
- **Found during:** Task 3 (adding settings path to segment_page())
- **Issue:** After refactoring, `provider_name` and `model` were only defined inside the `if provider is None:` branch, but the result dict below used them unconditionally — would raise NameError when settings.json provider was used
- **Fix:** Added `else` branch after the `if provider is None:` block setting `provider_name = settings.get('backend', 'openai_compatible')` and `model = settings.get('model', '')`
- **Files modified:** app.py
- **Verification:** All 15 new tests pass including test_segment_uses_settings_json
- **Committed in:** 53da80a (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Auto-fix essential for correctness — segment_page() would have crashed on first settings-based segmentation call. No scope creep.

## Issues Encountered
None beyond the above deviation.

## User Setup Required
None - no external service configuration required at this phase. Operators will configure API key via the settings UI (Phase 17-02 frontend).

## Next Phase Readiness
- Backend fully implemented: GET/POST /settings, GET /settings/models, segment_page() reads settings.json
- Ready for Phase 17-02: VLM Settings UI frontend (settings panel in upload.html)
- No blockers

---
*Phase: 17-vlm-settings-ui*
*Completed: 2026-03-01*
