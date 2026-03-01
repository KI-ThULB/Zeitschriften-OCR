---
phase: 17-vlm-settings-ui
plan: 02
subsystem: ui
tags: [html, css, javascript, vlm, settings, fetch, openwebui, openrouter]

# Dependency graph
requires:
  - phase: 17-vlm-settings-ui (17-01)
    provides: GET/POST /settings, GET /settings/models backend endpoints
  - phase: 13-upload-ui-and-live-progress
    provides: upload.html dashboard base template
provides:
  - VLM Settings panel in upload.html (CSS + HTML + JS)
  - BACKEND_PRESETS constant with Open WebUI and OpenRouter curated model lists
  - populateModelDropdown(), onBackendChange(), loadModels(), saveSettings(), initSettings() functions
  - Settings panel restores persisted settings on page load via GET /settings
affects: [operators configuring VLM without CLI flags, Phase 18 Article Browser and Full-Text Search]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Backend radio + preset object pattern (BACKEND_PRESETS keyed by radio value)
    - Graceful fallback: loadModels() shows curated list on API error, never leaves dropdown empty
    - initSettings() merges saved model with preset list (prepends if not in curated list)
    - Silent best-effort init — initSettings() catches all errors so page load never breaks

key-files:
  created: []
  modified:
    - templates/upload.html

key-decisions:
  - "BACKEND_PRESETS object keyed by radio value — onBackendChange() reads preset directly without branching"
  - "initSettings() prepends saved model to preset list if not already included — handles custom/live models persisted from a prior loadModels() session"
  - "loadModels() falls back to curated list (not empty dropdown) on API error — panel always usable offline"
  - "saveSettings() clears status text after 3s only if text still matches — prevents clearing a subsequent error message"

patterns-established:
  - "Settings UI pattern: radio presets update derived fields (base URL, model list) via onBackendChange()"
  - "initSettings() always runs after populateModelDropdown() in DOMContentLoaded — init overwrites defaults with persisted values"

requirements-completed: [STRUCT-02]

# Metrics
duration: 42min
completed: 2026-03-02
---

# Phase 17 Plan 02: VLM Settings UI Frontend Summary

**VLM Settings panel in upload.html with backend radio presets (Open WebUI / OpenRouter), live model fetch with curated fallback, and persist/restore via GET/POST /settings**

## Performance

- **Duration:** 42 min (including human verification round-trip)
- **Started:** 2026-03-01T22:44:20Z
- **Completed:** 2026-03-01T23:26:05Z
- **Tasks:** 1 auto + 1 human-verify (approved)
- **Files modified:** 1 (templates/upload.html, 274 lines added)

## Accomplishments
- VLM Settings section added below "Download METS" button — backend radios, base URL input, API key password input, model dropdown, "Load models" button, "Save Settings" button, status div
- BACKEND_PRESETS with full curated model lists for Open WebUI (5 vision models) and OpenRouter (10 vision models); switching radio updates base URL and model dropdown instantly
- loadModels() fetches GET /settings/models and populates dropdown; falls back to curated list with inline error message if API call fails — panel always usable
- saveSettings() POSTs to /settings; shows green "Saved" for 3 seconds then clears
- initSettings() fetches GET /settings on page load and restores base URL, radio selection, API key, and model (prepending saved model to list if not in curated set)
- All 116 tests pass with zero regressions; human verification passed all 8 browser checks

## Task Commits

Each task was committed atomically:

1. **Task 1: Add VLM Settings panel to upload.html** - `b007c67` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `templates/upload.html` - Added CSS (#vlm-settings, .settings-row, .backend-radios, #btn-load-models, #btn-save-settings, #settings-status), HTML (VLM Settings div with all controls), JS (BACKEND_PRESETS, getSelectedBackend, populateModelDropdown, onBackendChange, loadModels, saveSettings, initSettings), DOMContentLoaded init calls

## Decisions Made
- BACKEND_PRESETS object keyed by radio value lets onBackendChange() read preset without branching — adding a third backend only requires a new key
- initSettings() prepends saved model to preset list if not already there — handles custom/live models from a previous loadModels() session surviving page reload
- loadModels() always falls back to curated list on error (never empty dropdown) — panel stays usable when server is air-gapped or API key not yet entered
- saveSettings() conditional clear: `if (status.textContent === '\u2713 Settings saved')` prevents the setTimeout from wiping a subsequent error message

## Deviations from Plan

None - plan executed exactly as written.

Note: Two hotfixes in vlm.py were committed separately by the user during human verification (max_tokens 2048→4096, _parse_regions() markdown fence stripping). These were out-of-scope for this plan and committed independently — not tracked as deviations here.

## Issues Encountered
None.

## User Setup Required
None - settings panel is the UI for entering credentials. No server-side configuration needed.

## Next Phase Readiness
- Phase 17 complete: VLM Settings backend (17-01) + frontend panel (17-02) fully functional
- Operators can configure Open WebUI or OpenRouter from the browser without CLI flags
- Settings persist to output/settings.json; Segment button in viewer uses saved config automatically
- Ready for Phase 18: Article Browser and Full-Text Search

---
*Phase: 17-vlm-settings-ui*
*Completed: 2026-03-02*
