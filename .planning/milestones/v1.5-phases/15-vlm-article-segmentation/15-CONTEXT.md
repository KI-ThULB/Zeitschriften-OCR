# Phase 15 Context — VLM Article Segmentation

## Goal

Operators can trigger automatic article segmentation for any page using a configurable VLM provider.
The system identifies article regions with bounding boxes, types, titles, and stores results per page.

## Requirements Covered

- STRUCT-01: Configurable VLM provider via `--vlm-provider` / `--vlm-model` CLI flags or env vars
- STRUCT-02: Detected regions have bounding box, type (headline/article/advertisement/illustration/caption), stored in `output/segments/<stem>.json`
- STRUCT-03: Each region has a title and section type extracted as structured metadata

## Key Design Decisions

### Provider Abstraction (`vlm.py`)

Single module at project root. Three classes:

```
SegmentationProvider  (base, raises NotImplementedError)
  ClaudeProvider      (anthropic SDK, lazy import)
  OpenAIProvider      (openai SDK, lazy import)
```

Factory: `get_provider(name, model, api_key) -> SegmentationProvider`

Both providers call `_parse_regions(text) -> list[dict]` to extract structured output from the VLM response text.

### VLM Prompt

```
Analyze this newspaper page and identify distinct article regions.
For each region output:
  - type: one of "headline", "article", "advertisement", "illustration", "caption"
  - title: brief descriptive title (article headline if visible, otherwise a short description)
  - bounding_box: {x, y, width, height} as floats 0.0–1.0 (fraction of image dimensions)

Respond ONLY with valid JSON:
{"regions": [{"type": "...", "title": "...", "bounding_box": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.2}}, ...]}

If no article regions are detectable, respond with: {"regions": []}
```

Bounding boxes use **normalized coordinates** (0.0–1.0 fraction of JPEG dimensions), not pixel values.
This is more portable across zoom levels and matches how the viewer scales images.

### Region Parsing (`_parse_regions`)

- Uses `re.search(r'\{[\s\S]*\}', text)` to extract JSON from VLM response (handles preamble/postamble)
- Filters out regions with invalid type (not in VALID_TYPES)
- Assigns sequential IDs: `r0`, `r1`, ...
- Returns `[]` (not error) on any parse failure — satisfies SC-4 (empty list vs error)

### Storage

Path: `output/segments/<stem>.json`

Format:
```json
{
  "stem": "page_001",
  "provider": "claude",
  "model": "claude-opus-4-6",
  "segmented_at": "2026-03-01T12:00:00",
  "regions": [
    {
      "id": "r0",
      "type": "article",
      "title": "Article Title",
      "bounding_box": {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.3}
    }
  ]
}
```

### Flask Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/segment/<stem>` | POST | Trigger VLM segmentation; store + return regions |
| `/segment/<stem>` | GET | Return stored regions JSON; 404 if not yet segmented |

POST response shape:
```json
{"stem": "...", "provider": "...", "model": "...", "segmented_at": "...", "regions": [...]}
```

Status codes:
- 200: success (POST returns result; GET returns stored)
- 400: path traversal
- 404: POST — JPEG not in cache; GET — no stored segments file
- 503: VLM provider not configured
- 502: VLM API call failed

### JPEG Source

The endpoint reads from `output/jpegcache/<stem>.jpg` (populated by `/image/<stem>`).
If the cache file doesn't exist, returns 404 with message: "image not found — open the viewer for this file first".
This is safe because the viewer always calls `/image/<stem>` on file load.

### API Key Resolution

In the POST /segment endpoint:
```python
api_key = app.config.get('VLM_API_KEY') or os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY', '')
```

CLI flag `--vlm-api-key` populates `app.config['VLM_API_KEY']`.
Env vars serve as fallback (preferred for security — no plaintext key in shell history).

### Package Dependencies

- `anthropic>=0.40.0` — lazy-imported inside `ClaudeProvider.segment()`
- `openai>=1.0.0` — lazy-imported inside `OpenAIProvider.segment()`

Both are optional at import time (only needed if that provider is used).
Add both to `requirements.txt` so they're available without extra install steps.

### Test Strategy

Mock `vlm.get_provider` factory to return a `MagicMock` provider — no actual API calls in tests.
Use `monkeypatch.setattr(app_module, 'vlm', ...)` or `monkeypatch.setattr(app_module.vlm, 'get_provider', ...)`.

Import pattern in tests:
```python
import importlib
app_module = importlib.import_module('app')
import vlm
```

## Region Overlay (Plan 15-02)

Regions are drawn as colored SVG `<rect>` elements on the existing `#overlay` SVG.
Coordinates: normalized 0–1 values × `jpeg_width`/`jpeg_height` (same coordinate space as ALTO words).
The shared-container transform from Phase 14 means region rects zoom/pan automatically — no extra transform needed.

Color by type:
- headline: `rgba(255, 100, 100, 0.35)` (red)
- article: `rgba(100, 150, 255, 0.25)` (blue)
- advertisement: `rgba(255, 200, 50, 0.30)` (yellow)
- illustration: `rgba(100, 220, 100, 0.30)` (green)
- caption: `rgba(200, 100, 255, 0.25)` (purple)

A `<text>` label showing `type: title` is rendered inside each rect (truncated at 40 chars).

`loadFile()` calls `GET /segment/<stem>` to restore previously computed regions (200 → draw; 404 → clear).
