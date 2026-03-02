# Phase 17: VLM Settings UI — Context

## Problem

Article segmentation currently requires CLI flags (`--vlm-provider`, `--vlm-model`, `--vlm-api-key`).
Operators using the web interface have no way to configure VLM settings without restarting the server.
When no provider is configured, the Segment button shows "VLM not configured on this server" — a dead end.

## Goal

A settings panel on the upload dashboard lets operators enter their API key, pick a backend, and save.
Settings persist to `output/settings.json`. The Segment button works without CLI flags after saving.

## Backend Design

### New provider: OpenAICompatibleProvider

Both Open WebUI and OpenRouter use the OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`).
A single `OpenAICompatibleProvider(model, api_key, base_url)` handles both, using `openai.OpenAI(base_url=..., api_key=...)`.

Provider routing: backend value `'openai_compatible'` → `OpenAICompatibleProvider`.
Existing `'claude'` and `'openai'` providers unchanged.

### Settings schema (`output/settings.json`)

```json
{
  "backend": "openai_compatible",
  "base_url": "https://openwebui-workshop.test.uni-jena.de/ollama/v1",
  "api_key": "...",
  "model": "llama3.2-vision:latest"
}
```

Fields:
- `backend`: `"openai_compatible"` (only value for now; extensible)
- `base_url`: full base URL including `/v1` suffix
- `api_key`: API key or JWT token
- `model`: model identifier string

### Precedence in segment_page()

1. `output/settings.json` (if exists and has a backend)
2. `app.config['VLM_PROVIDER']` (CLI flags, legacy)
3. 503 "not configured"

### New endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /settings | Return current settings JSON (200) or `{}` if none |
| POST | /settings | Accept JSON body, validate, write settings.json (200) |
| GET | /settings/models | Fetch live model list from base_url + /models using api_key (200 with list or 502) |

GET /settings/models requires `base_url` and `api_key` query params.

## Frontend Design

Settings section at bottom of upload.html (below METS export).

### Layout

```
[ VLM Settings ]────────────────────────────────────────
Backend:    [● Open WebUI (Uni Jena)  ○ OpenRouter]
Base URL:   [https://openwebui-workshop.test.uni-jena.de/ollama/v1    ]
API Key:    [••••••••••••••••••••••••••••••••••]
Model:      [Select model ▼]  [Load models]
            [Save Settings]
            ✓ Settings saved  (or ✗ error message)
```

### Backend radio presets

**Open WebUI (Uni Jena)**:
- base_url: `https://openwebui-workshop.test.uni-jena.de/ollama/v1`
- Curated fallback models: `llama3.2-vision:latest`, `bakllava:latest`, `minicpm-v:latest`, `moondream:latest`, `granite3.2-vision:latest`

**OpenRouter**:
- base_url: `https://openrouter.ai/api/v1`
- Curated fallback models (top 10 vision):
  1. `google/gemini-flash-1.5`
  2. `openai/gpt-4o`
  3. `anthropic/claude-3-5-sonnet`
  4. `meta-llama/llama-3.2-90b-vision-instruct`
  5. `google/gemini-pro-1.5`
  6. `anthropic/claude-3-opus`
  7. `openai/gpt-4o-mini`
  8. `mistralai/pixtral-12b`
  9. `qwen/qwen-vl-max`
  10. `anthropic/claude-3-haiku`

### "Load models" button

Calls `GET /settings/models?base_url=...&api_key=...`, populates model dropdown with returned list.
Falls back to curated list if API call fails (shows toast).

### Save

POST /settings with JSON body. On 200: show "✓ Settings saved" for 3s.

### Init

On page load: fetch GET /settings, pre-fill fields if settings exist.
