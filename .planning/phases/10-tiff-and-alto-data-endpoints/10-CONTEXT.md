# Phase 10: TIFF and ALTO Data Endpoints - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Two read-only GET endpoints added to `app.py`: `GET /image/<stem>` serves a scaled JPEG of the uploaded TIFF, and `GET /alto/<stem>` returns a flat JSON word array with page and JPEG dimensions. Both verified against real TIFFs before the viewer (Phase 11) is built. No UI, no writes.

</domain>

<decisions>
## Implementation Decisions

### JPEG Scaling
- Scale to max 1600px on longest side (handles both portrait and landscape TIFFs correctly)
- Source TIFFs served from `uploads/` subfolder only — no fallback to CLI input path
- JPEG dimensions (jpeg_width, jpeg_height) returned by `/alto/<stem>` JSON — no custom response headers on the image endpoint

### JPEG Caching
- Cache rendered JPEG as `<stem>.jpg` in a `jpegcache/` subfolder inside the output directory
- No automatic cache invalidation — TIFFs don't change after upload; operator deletes `jpegcache/` manually if needed
- On request: serve cached file if exists, otherwise render from TIFF and write cache

### ALTO Word JSON Shape
- Flat array — all words in one list, no block/line nesting
- Top-level response: `{ page_width, page_height, jpeg_width, jpeg_height, words: [...] }`
- Per-word fields: `id`, `content`, `hpos`, `vpos`, `width`, `height`, `confidence`
- Words with no ALTO confidence attribute: include with `confidence: null` (not excluded, not coerced to 0)

### Error Handling
- Missing stem (TIFF or ALTO XML not found): `404` with JSON body `{"error": "not found", "stem": "<stem>"}`
- Corrupt or unreadable TIFF (Pillow failure): `500` with JSON error body
- Malformed ALTO XML (parse failure): `500` with JSON error body
- Path traversal in stem (contains `/` or `..`): `400` reject immediately

### ALTO JSON Caching
- No disk cache for ALTO JSON — parse XML on every request
- ALTO XML files are small (10–100 KB) and fast to parse; Phase 12 edits them directly, making a JSON cache a stale-data risk

### Claude's Discretion
- Exact JPEG quality setting (suggest 85)
- Pillow resampling filter (LANCZOS recommended for downscaling)
- JSON error body field names beyond `error` and `stem`
- How jpeg_width/jpeg_height are computed (from PIL image size after resize)

</decisions>

<specifics>
## Specific Ideas

- Scale factor for overlay alignment: `scale_x = rendered_width / page_width` — the four dimension fields in the ALTO response are what make this possible without any additional client state
- The `jpegcache/` folder sits alongside `uploads/` and `alto/` in the output directory

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-tiff-and-alto-data-endpoints*
*Context gathered: 2026-02-27*
