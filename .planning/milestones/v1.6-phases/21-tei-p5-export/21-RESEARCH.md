# Phase 21: TEI P5 Export - Research

**Researched:** 2026-03-03
**Domain:** TEI P5 XML generation from ALTO 2.1 + VLM segmentation data; Flask download endpoint
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Export scope and trigger
- **Unit:** Single page — one TEI document per currently loaded TIFF file
- **Trigger:** "Download TEI" button in the top toolbar header area of the viewer (alongside file name / existing page-level controls)
- **Output saved to disk:** `output/tei/<stem>.xml` — alongside `output/alto/` and `output/mets/`
- **Also served as HTTP response:** Browser download triggered by the same Flask endpoint that writes the file
- **No VLM data for page:** Export proceeds anyway; XML comment inserted noting VLM data was absent; all text rendered as one `<div type="article">` with paragraph role

#### Text content
- **Word source:** Normalized display words — column-sorted (left-to-right reading order), hyphens rejoined (e.g. "Verbindung" not "Ver-" + "bindung")
- **Source of truth:** ALTO XML on disk — corrections saved via the editor are already written back to ALTO, so reading from disk captures them automatically
- **Low-confidence words:** Plain text, no special TEI annotation (no `<unclear>`, no `@cert`)
- **`<lb/>` placement:** Inserted after each line-terminal word; for rejoined hyphenated words, `<lb/>` appears after the rejoined form (e.g. `Verbindung<lb/>`)

#### TEI header and metadata
- **Header source:** METS/MODS file at `output/mets/<stem>_mets.xml` if it exists; fall back to filename-derived title if absent
- **MODS fields to populate:** title + date + publisher/source (three fields); skip any field not present in MODS
- **encodingDesc:** Short boilerplate — tool name ("Zeitschriften-OCR") and generation date; no elaborate schema description

#### Facsimile and coordinate system
- **`<facsimile>` section:** One `<surface xml:id="page-{stem}">` per page; one `<zone>` per VLM article region
- **Zone coordinates:** ALTO pixel space — `ulx`, `uly`, `lrx`, `lry` attributes (VLM 0.0–1.0 fractional coords × pageWidth/pageHeight)
- **`<surface @facs>`:** Relative path to the TIFF in the input folder (e.g. `../scans/scan_001.tif`)

#### Edge case: no VLM data
- `<body>` contains one `<div type="article">` wrapping all detected paragraphs
- An XML comment is added at the top of `<body>`: `<!-- VLM segmentation absent: all text rendered as single article -->`
- No `<zone>` elements in `<facsimile>` when no VLM data; `<surface>` element still present

### Claude's Discretion
- Exact Flask endpoint path for the download (e.g. `/tei/<stem>` or `/export/tei/<stem>`)
- Whether to add a `<revisionDesc>` in teiHeader or leave it out
- Exact `<encodingDesc>` wording and element structure
- How `<pb>` is placed relative to `<body>` (before first word of page, or as a milestone element)
- METS parsing strategy (which XPath or namespace to use for MODS fields)

### Deferred Ideas (OUT OF SCOPE)
- `<choice><orig>Ver-</orig><reg>Verbindung</reg></choice>` elements for rejoined hyphens — TEI-04 in future requirements
- Per-article TEI export (TEI-05) — future phase
- Multi-page issue TEI combining all pages — future milestone
- `@cert` annotation for low-confidence words — out of scope for this phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEI-01 | System generates a TEI P5 XML document per processed issue combining all pages; each VLM-identified article appears as a `<div type="article">` with `@n` and title metadata | TEI P5 `div` structure with `type="article"` and `@n` confirmed in TEI guidelines; VLM region data available from `output/segments/<stem>.json` (`regions[].type`, `regions[].title`) |
| TEI-02 | TEI document preserves line structure via `<lb/>` elements and page transitions via `<pb n="N" facs="#page-N"/>` elements linked to JPEG images | `line_end` flag already returned by `/alto/<stem>` API (Phase 19); `<lb/>` placement after line-terminal word maps directly to the flag; `<pb facs="#page-{stem}"/>` links to `xml:id` on `<surface>` |
| TEI-03 | TEI document includes a `<facsimile>` section with one `<surface xml:id="page-N">` per page and `<zone>` elements for each article region carrying ALTO-derived coordinate attributes | `<surface>` and `<zone>` with `ulx/uly/lrx/lry` attributes confirmed in TEI P5 spec; VLM fractional bounding boxes converted via `bb.x * page_width` (pattern established in Phase 20) |
</phase_requirements>

---

## Summary

Phase 21 generates a TEI P5 XML document per TIFF page from three existing data sources: (1) ALTO 2.1 XML on disk for word content and line structure, (2) `output/segments/<stem>.json` for VLM article regions and bounding boxes, and (3) optionally `output/mets/<stem>_mets.xml` for MODS-derived title/date/publisher. The TEI namespace is `http://www.tei-c.org/ns/1.0`; the document root is `<TEI xmlns="http://www.tei-c.org/ns/1.0">` with teiHeader, facsimile, and text elements. All XML is built with `lxml.etree` (already a project dependency) using the same namespace-qualified element factory pattern as `mets.py`.

The `<lb/>` element in TEI P5 is a milestone element marking a line beginning — by convention placed before the new line's content. In practice for OCR export, the "after last word" pattern from CONTEXT.md is equivalent: the `<lb/>` appears after the last word of one line and before the first word of the next, producing the same document. The `line_end` flag already set per-word in `serve_alto()` drives this. VLM zone coordinates require the same `bb.x * page_width` conversion established in Phase 20 (using ALTO pixel space, not JPEG dimensions).

The Flask endpoint pattern to follow is `/mets` → `mets.build_mets()` → return `Response(xml_bytes, mimetype='application/xml', headers={'Content-Disposition': 'attachment; ...'})`; the TEI endpoint will do the same while also writing the file to `output/tei/<stem>.xml` before returning. A "Download TEI" button in the `#nav-bar` triggers `window.location = '/tei/<stem>'` for the currently loaded page.

**Primary recommendation:** Create `tei.py` mirroring `mets.py` in structure (single `build_tei(output_dir, stem)` function), add a `GET /tei/<stem>` endpoint in `app.py` that writes `output/tei/<stem>.xml` and returns it as a download attachment, and add a "Download TEI" button to the `#nav-bar` in `viewer.html`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | >=5.3.0 (already in requirements.txt) | Build TEI XML with namespace-qualified elements | Already used for ALTO and METS generation; handles xml:id and mixed content correctly |
| Flask | >=3.1.0 (already in requirements.txt) | HTTP endpoint for download trigger | Existing web framework; `/mets` download pattern is identical |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | File system paths for output/tei/, output/alto/, output/segments/ | Used throughout existing codebase |
| json | stdlib | Parse `output/segments/<stem>.json` for article regions | Same pattern as `mets.py` |
| datetime | stdlib | Generation timestamp in encodingDesc | Same pattern as mets.py `metsHdr` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| lxml.etree | xml.etree.ElementTree | lxml handles xml:id namespace, mixed content (lb/pb milestones), and xml_declaration correctly; stdlib ET does not emit `<?xml?>` declaration reliably and has no namespace-aware pretty printing |
| lxml.etree | xmltodict or template string | For structured XML with namespaces and milestone elements, programmatic lxml is safer — avoids injection, handles encoding |

**Installation:**

No new dependencies required. `lxml>=5.3.0` is already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
tei.py                      # New module — mirrors mets.py in structure
output/
└── tei/
    └── <stem>.xml          # Generated TEI file per page (created by endpoint)
tests/
└── test_tei.py             # New test module — mirrors test_mets.py pattern
```

The `tei.py` module lives at the project root alongside `pipeline.py`, `mets.py`, `vlm.py`, `search.py`.

### Pattern 1: TEI Document Structure

**What:** `<TEI>` root with three direct children: `<teiHeader>`, `<facsimile>`, `<text>`

**The spec-confirmed structure:**
```xml
<?xml version='1.0' encoding='UTF-8'?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>...</title></titleStmt>
      <publicationStmt><p>...</p></publicationStmt>
      <sourceDesc><p>...</p></sourceDesc>
    </fileDesc>
    <encodingDesc>
      <projectDesc><p>Generated by Zeitschriften-OCR on ...</p></projectDesc>
    </encodingDesc>
  </teiHeader>
  <facsimile>
    <surface xml:id="page-{stem}" ulx="0" uly="0" lrx="{page_width}" lry="{page_height}"
             facs="../uploads/{stem}.tif">
      <zone xml:id="zone-{stem}-r0" ulx="..." uly="..." lrx="..." lry="..."
            type="article"/>
    </surface>
  </facsimile>
  <text>
    <body>
      <pb n="1" facs="#page-{stem}"/>
      <div type="article" n="1">
        <head>Article Title</head>
        <p>Word1 Word2<lb/>Word3 Word4<lb/>Word5</p>
      </div>
    </body>
  </text>
</TEI>
```

### Pattern 2: lxml namespace-qualified builder (confirmed working in project)

**What:** Use Clark notation `{ns}tag` for all elements; pass `nsmap={None: TEI_NS}` on root only

```python
# Source: verified in lxml, matches mets.py pattern
TEI_NS = 'http://www.tei-c.org/ns/1.0'
XML_NS = 'http://www.w3.org/XML/1998/namespace'

def _t(tag: str) -> str:
    return f'{{{TEI_NS}}}{tag}'

nsmap = {None: TEI_NS}
root = etree.Element(_t('TEI'), nsmap=nsmap)

# xml:id attribute — use Clark notation for XML namespace
surface = etree.SubElement(facs_elem, _t('surface'),
    **{f'{{{XML_NS}}}id': f'page-{stem}'},
    ulx='0', uly='0', lrx=str(page_width), lry=str(page_height))
```

The `nsmap={None: TEI_NS}` on root propagates to all descendants — no need to repeat on child elements.

### Pattern 3: Mixed content with lb/pb milestone elements

**What:** `<lb/>` and `<pb/>` are empty milestone elements inserted into text flow using lxml's `.tail` attribute pattern

```python
# After the last word of a line, insert <lb/> with the next line's text as .tail
# Pattern verified with lxml for this project:
p_elem = etree.SubElement(div, _t('p'))
p_elem.text = 'First word on line'

lb = etree.SubElement(p_elem, _t('lb'))
lb.tail = 'First word of next line'

lb2 = etree.SubElement(p_elem, _t('lb'))
lb2.tail = 'First word of third line'
# Result: <p>First word on line<lb/>First word of next line<lb/>First word of third line</p>
```

**IMPORTANT:** The `line_end` flag in the `/alto/<stem>` API marks the last `String` in each `TextLine`. When building the TEI, after emitting the text for a word with `line_end=True`, insert an `<lb/>` element before emitting the next word (set the lb's `.tail` to the next word's text). The final word of a `<p>` does NOT get an `<lb/>` after it — only inter-line boundaries get markers.

### Pattern 4: Column sort and hyphen rejoin in Python (server-side)

**What:** The normalization pipeline lives in the frontend (JavaScript). The TEI builder must re-implement column sort and hyphen rejoin in Python, reading from the ALTO data.

The ALTO data returned by `serve_alto()` already has `line_end` and `blocks` with HPOS data. The TEI builder reads ALTO directly (same as `mets.py` does), but must replicate:

1. **Column sort:** Group TextBlocks by HPOS clustering (gap > 20% page_width separates columns); sort full-width blocks first (>60% page width), then column blocks left-to-right, then top-to-bottom within each column
2. **Hyphen rejoin:** Walk words in sorted order; if a word ends in `-` and has `line_end=True`, concatenate with the next word and suppress the intermediate `<lb/>`

```python
# Column sort logic — replicates viewer.html columnSort() in Python
def _column_sort(strings: list[dict], page_width: int) -> list[dict]:
    """Sort ALTO String elements in multi-column reading order."""
    # Each string dict: {elem, hpos, vpos, block_hpos, block_width}
    # Group into column clusters by block HPOS gaps > 0.2 * page_width
    ...

# Hyphen rejoin — replicates viewer.html rejoinHyphens() in Python
def _rejoin_hyphens(words: list[dict]) -> list[dict]:
    """Merge end-of-line hyphenated words; mark rejoined as line_end=False."""
    ...
```

### Pattern 5: VLM region mapping to TEI articles

**What:** Each VLM region in `segments/<stem>.json` maps to one `<div type="article">` and one `<zone>` in `<facsimile>`

```python
# From segments JSON:
# { "id": "r0", "type": "article", "title": "Die Macht...",
#   "bounding_box": {"x": 0.25, "y": 0.0, "width": 0.49, "height": 0.5} }
#
# Map to facsimile zone:
ulx = int(bb['x'] * page_width)
uly = int(bb['y'] * page_height)
lrx = int((bb['x'] + bb['width']) * page_width)
lry = int((bb['y'] + bb['height']) * page_height)

zone = etree.SubElement(surface, _t('zone'),
    **{f'{{{XML_NS}}}id': f'zone-{stem}-{region["id"]}'},
    ulx=str(ulx), uly=str(uly), lrx=str(lrx), lry=str(lry),
    type=region.get('type', 'article'))

# Map to body div:
div = etree.SubElement(body, _t('div'), type='article')
div.set('n', str(n))
if region.get('title'):
    head = etree.SubElement(div, _t('head'))
    head.text = region['title']
```

### Pattern 6: Assign words to article regions

**What:** For each article `<div>`, identify which ALTO words fall within the VLM bounding box using the same intersection logic as `mets.py._find_word_ids_in_region()`

The TEI builder needs to assign words to article divs. Use the same overlap test as `mets.py`:

```python
hpos_min = bb['x'] * page_width
vpos_min = bb['y'] * page_height
hpos_max = (bb['x'] + bb['width']) * page_width
vpos_max = (bb['y'] + bb['height']) * page_height

for s in all_strings:
    hpos = float(s.get('HPOS', 0))
    vpos = float(s.get('VPOS', 0))
    w = float(s.get('WIDTH', 0))
    h = float(s.get('HEIGHT', 0))
    if hpos < hpos_max and (hpos + w) > hpos_min \
       and vpos < vpos_max and (vpos + h) > vpos_min:
        # word belongs to this article region
```

Words not overlapping any region go into an "uncategorized" div or the single fallback div (no VLM case).

### Pattern 7: Flask download endpoint

**What:** Mirrors the `/mets` endpoint: build XML, write to disk, return as attachment

```python
@app.get('/tei/<stem>')
def export_tei(stem):
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_path = output_dir / 'alto' / (stem + '.xml')
    if not alto_path.exists():
        return jsonify({'error': 'not found', 'stem': stem}), 404

    try:
        import tei as tei_module
        xml_bytes = tei_module.build_tei(output_dir, stem)
    except Exception as exc:
        return jsonify({'error': 'TEI build failed', 'detail': str(exc)}), 500

    tei_dir = output_dir / 'tei'
    tei_dir.mkdir(exist_ok=True)
    tei_path = tei_dir / (stem + '.xml')
    tei_path.write_bytes(xml_bytes)

    return Response(
        xml_bytes,
        status=200,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename="{stem}_tei.xml"'},
    )
```

### Pattern 8: MODS metadata extraction

**What:** Try to read `output/mets/<stem>_mets.xml` for title/date/publisher; fall back to stem-derived title

**Important note:** The current codebase does NOT write per-stem METS files to disk — `mets.py` generates XML on-demand. The `output/mets/` directory does not exist yet. The CONTEXT.md says to read from `output/mets/<stem>_mets.xml` if it exists; since it will not exist in practice, the fallback (filename-derived title) will always be used until a future phase writes per-stem METS files.

```python
MODS_NS = 'http://www.loc.gov/mods/v3'

def _read_mods_metadata(output_dir: Path, stem: str) -> dict:
    """Read title/date/publisher from per-stem METS file if present."""
    mets_path = output_dir / 'mets' / (stem + '_mets.xml')
    result = {'title': None, 'date': None, 'publisher': None}
    if not mets_path.exists():
        return result
    try:
        root = etree.parse(str(mets_path)).getroot()
        ns = {'mods': MODS_NS}
        result['title'] = root.findtext('.//mods:title', namespaces=ns)
        result['date'] = root.findtext('.//mods:dateIssued', namespaces=ns)
        result['publisher'] = root.findtext('.//mods:publisher', namespaces=ns)
    except Exception:
        pass
    return result
```

### Anti-Patterns to Avoid

- **Using string formatting/templates for XML:** Namespace handling breaks, special characters aren't escaped. Always use `lxml.etree`.
- **Putting `<lb/>` after the LAST word in a paragraph:** The final word in a `<p>` gets no trailing `<lb/>`. Only inter-line boundaries inside a paragraph get `<lb/>` markers.
- **Using `facs="page-{stem}"` without the `#` prefix:** The `facs` attribute on `<pb>` must use fragment identifier syntax: `facs="#page-{stem}"` (with hash). The `<surface xml:id>` does NOT have the hash.
- **Applying JPEG dimensions instead of ALTO page dimensions for zone coordinates:** Zone coordinates must be in ALTO pixel space (`page_width`/`page_height` from `<Page WIDTH= HEIGHT=>`), not JPEG dimensions. This is the same trap noted in Phase 20 accumulated context.
- **Adding `<lb/>` for rejoined hyphenated words:** When two words are rejoined ("Ver-" + "bindung" → "Verbindung"), the intermediate `<lb/>` is suppressed. The `<lb/>` only appears after the rejoined word (i.e., at the NEXT actual line break after the rejoined form), per CONTEXT.md.
- **Forgetting `xml:id` uses XML namespace:** In lxml, `xml:id` is `{http://www.w3.org/XML/1998/namespace}id`, not the string `"xml:id"`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML generation with namespace | String concat or f-string templates | `lxml.etree` | Namespace propagation, attribute escaping, xml:id handling |
| Column sorting logic | New algorithm | Port `columnSort()` from viewer.html JS to Python | Logic already proven in production; same ALTO block data |
| Word-to-region assignment | New spatial overlap | Copy `_find_word_ids_in_region()` from `mets.py` | Already handles ALTO pixel-space overlap correctly |
| File download response | Custom file server | Flask `Response` with `Content-Disposition: attachment` | Matches existing `/mets` pattern exactly |

**Key insight:** All the hard logic (column sort, hyphen rejoin, region overlap, coordinate conversion) already exists in the frontend JavaScript or `mets.py`. The TEI module is primarily a translation layer.

---

## Common Pitfalls

### Pitfall 1: facs attribute missing hash prefix
**What goes wrong:** `<pb facs="page-scan001"/>` — the `facs` attribute points to nothing; XML is well-formed but the link is broken
**Why it happens:** Confusion between the `xml:id` value (`page-scan001`) and the fragment identifier that references it (`#page-scan001`)
**How to avoid:** Always `facs="#page-{stem}"` on `<pb>` and `<div facs="...">` elements; `xml:id="page-{stem}"` (no hash) on `<surface>`
**Warning signs:** TEI requirement TEI-04 (facs references resolve) fails if hash is omitted

### Pitfall 2: Zone coordinates in JPEG space instead of ALTO space
**What goes wrong:** Zones are misaligned by a scale factor — accurate on small TIFFs, wrong on 10077×7528 originals
**Why it happens:** Using `jpeg_width`/`jpeg_height` instead of `page_width`/`page_height` from ALTO `<Page>`
**How to avoid:** Always read `page_width = int(page.get('WIDTH'))` from ALTO XML; match the pattern from Phase 20 accumulated context: "bb.x * pageWidth not jpeg_width"
**Warning signs:** Zone coordinates are smaller than expected for large-format TIFFs

### Pitfall 3: lb after last word of paragraph
**What goes wrong:** Trailing `<lb/>` after the final word of a `<p>`, or after the last `<p>` of a `<div>`
**Why it happens:** Iterating words and always appending `<lb/>` when `line_end=True` without checking if it's also the last word in the group
**How to avoid:** Track position within the word group; only insert `<lb/>` between consecutive lines, not after the final line
**Warning signs:** TEI validators warn about trailing milestone elements; scholarly tools may produce extra blank lines

### Pitfall 4: Hyphen rejoin loses the intermediate lb
**What goes wrong:** "Ver-<lb/>bindung" appears in TEI instead of "Verbindung<lb/>" (where `<lb/>` represents the next line break after the rejoined form)
**Why it happens:** Applying `line_end` flag verbatim without rejoining first
**How to avoid:** Rejoin hyphens FIRST (like `rejoinHyphens()` in the frontend), then apply `line_end` flags to the resulting merged words. The rejoined word inherits the `line_end=False` status from the first fragment; the `line_end=True` from the second fragment (which is now consumed) is dropped.
**Warning signs:** Hyphenated words appear split with `<lb/>` between them

### Pitfall 5: lxml proxy recycling for TextLine last-String detection
**What goes wrong:** `line_end` detection fails for some lines when `id()` of lxml proxy objects is not stable
**Why it happens:** lxml recycles proxy objects — calling `root.iter()` twice may return different Python object ids for the same XML node
**How to avoid:** Materialise all String elements once into a list (as in `serve_alto()`); use `(CONTENT, HPOS, VPOS)` tuple as fallback lookup key. This exact pattern is documented in Phase 19-01 accumulated context and already in `serve_alto()`.
**Warning signs:** Some lines missing `<lb/>` markers, or `<lb/>` on wrong boundaries

### Pitfall 6: Missing tei output directory
**What goes wrong:** `tei_path.write_bytes()` raises `FileNotFoundError` because `output/tei/` doesn't exist
**Why it happens:** The `output/tei/` directory is new — not created by any earlier phase
**How to avoid:** `tei_dir.mkdir(parents=True, exist_ok=True)` before writing
**Warning signs:** 500 error on first TEI download; subsequent downloads succeed if created manually

---

## Code Examples

Verified patterns from official sources and existing project code:

### TEI namespace setup (verified: lxml output confirmed)
```python
# Source: verified via lxml 5.3.0 in this project
TEI_NS = 'http://www.tei-c.org/ns/1.0'
XML_NS = 'http://www.w3.org/XML/1998/namespace'  # for xml:id

def _t(tag: str) -> str:
    """Return Clark-notation tag in TEI namespace."""
    return f'{{{TEI_NS}}}{tag}'

nsmap = {None: TEI_NS}
root = etree.Element(_t('TEI'), nsmap=nsmap)
# Result: <TEI xmlns="http://www.tei-c.org/ns/1.0">
```

### Minimal teiHeader (confirmed: TEI P5 v4.11.0 spec)
```python
# Source: https://tei-c.org/release/doc/tei-p5-doc/en/html/examples-teiHeader.html
header = etree.SubElement(root, _t('teiHeader'))
file_desc = etree.SubElement(header, _t('fileDesc'))

title_stmt = etree.SubElement(file_desc, _t('titleStmt'))
etree.SubElement(title_stmt, _t('title')).text = title_text

pub_stmt = etree.SubElement(file_desc, _t('publicationStmt'))
etree.SubElement(pub_stmt, _t('p')).text = 'Generated by Zeitschriften-OCR'

source_desc = etree.SubElement(file_desc, _t('sourceDesc'))
etree.SubElement(source_desc, _t('p')).text = f'OCR output: {stem}.tif'

# encodingDesc (Claude's discretion — minimal boilerplate)
enc_desc = etree.SubElement(header, _t('encodingDesc'))
proj_desc = etree.SubElement(enc_desc, _t('projectDesc'))
etree.SubElement(proj_desc, _t('p')).text = (
    f'Generated by Zeitschriften-OCR on {datetime.now(timezone.utc).date().isoformat()}'
)
```

### facsimile section with surface and zone (confirmed: TEI P5 spec)
```python
# Source: https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-surface.html
#         https://www.tei-c.org/release/doc/tei-p5-doc/en/html/ref-zone.html
facs_elem = etree.SubElement(root, _t('facsimile'))
surface = etree.SubElement(
    facs_elem, _t('surface'),
    **{f'{{{XML_NS}}}id': f'page-{stem}'},
    ulx='0', uly='0',
    lrx=str(page_width), lry=str(page_height),
    facs=f'../uploads/{stem}.tif',
)

for i, region in enumerate(regions):
    bb = region['bounding_box']
    ulx = int(bb['x'] * page_width)
    uly = int(bb['y'] * page_height)
    lrx = int((bb['x'] + bb['width']) * page_width)
    lry = int((bb['y'] + bb['height']) * page_height)
    etree.SubElement(
        surface, _t('zone'),
        **{f'{{{XML_NS}}}id': f'zone-{stem}-{region["id"]}'},
        ulx=str(ulx), uly=str(uly), lrx=str(lrx), lry=str(lry),
        type=region.get('type', 'article'),
    )
```

### pb milestone and body structure (confirmed: TEI P5 spec)
```python
# Source: https://www.tei-c.org/release/doc/tei-p5-doc/en/html/ref-pb.html
text_elem = etree.SubElement(root, _t('text'))
body = etree.SubElement(text_elem, _t('body'))

# pb goes at start of body — single-page document
pb = etree.SubElement(body, _t('pb'), n='1', facs=f'#page-{stem}')
```

### Mixed content with lb (verified: lxml output confirmed)
```python
# Source: verified via lxml 5.3.0 in this project
# words_in_line_group: list of (content: str, is_line_end: bool)
p_elem = etree.SubElement(div, _t('p'))
pending_text = []

for j, (content, is_line_end) in enumerate(words_in_line_group):
    is_last = (j == len(words_in_line_group) - 1)
    pending_text.append(content)

    if is_line_end and not is_last:
        # Flush pending words, insert lb milestone
        text_segment = ' '.join(pending_text)
        if len(p_elem) == 0:
            # No children yet — set .text
            p_elem.text = (p_elem.text or '') + text_segment
        else:
            # Append to last child's .tail
            p_elem[-1].tail = (p_elem[-1].tail or '') + text_segment
        lb = etree.SubElement(p_elem, _t('lb'))
        lb.tail = ''  # next word will set this
        pending_text = []

# Flush remaining words (no trailing lb)
if pending_text:
    text_segment = ' '.join(pending_text)
    if len(p_elem) == 0:
        p_elem.text = (p_elem.text or '') + text_segment
    else:
        p_elem[-1].tail = (p_elem[-1].tail or '') + text_segment
```

### XML serialization (matches existing mets.py pattern)
```python
# Source: mets.py line 217 — existing project pattern
return etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
```

### ALTO reading pattern (from serve_alto() and mets.py)
```python
# Source: app.py serve_alto(), mets.py build_mets() — existing project patterns
from lxml import etree
import pipeline  # for ALTO21_NS

root = etree.parse(str(alto_path)).getroot()
ns = pipeline.ALTO21_NS  # 'http://schema.ccs-gmbh.com/ALTO'

page = root.find(f'.//{{{ns}}}Page')
page_width = int(page.get('WIDTH', 0))
page_height = int(page.get('HEIGHT', 0))

# Materialise once to avoid proxy recycling (Phase 19-01 pattern)
all_strings = list(root.iter(f'{{{ns}}}String'))
```

### Download endpoint pattern (from mets endpoint in app.py)
```python
# Source: app.py export_mets() — existing project pattern
@app.get('/tei/<stem>')
def export_tei(stem):
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400
    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_path = output_dir / 'alto' / (stem + '.xml')
    if not alto_path.exists():
        return jsonify({'error': 'not found', 'stem': stem}), 404
    try:
        xml_bytes = tei_module.build_tei(output_dir, stem)
    except Exception as exc:
        return jsonify({'error': 'TEI build failed', 'detail': str(exc)}), 500
    tei_dir = output_dir / 'tei'
    tei_dir.mkdir(parents=True, exist_ok=True)
    (tei_dir / (stem + '.xml')).write_bytes(xml_bytes)
    return Response(
        xml_bytes,
        status=200,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename="{stem}_tei.xml"'},
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TEI P5 Version 4.x | TEI P5 Version 4.11.0 | February 2026 | Stable — no breaking changes to facsimile/surface/zone/lb/pb elements |
| Separate ALTO-to-TEI XSLT stylesheets | Python/lxml direct generation | Project decision | Simpler, no Saxon dependency, same pattern as existing mets.py |
| Storing struct roles in separate JSON | Deriving struct roles dynamically from VLM region overlap | Phase 20 decision | TEI builder must replicate assignRoles() logic from viewer.html |

**Deprecated/outdated:**
- The TEI XML namespace was previously `http://www.tei-c.org/ns/2.0` in some older tools: the current canonical namespace is `http://www.tei-c.org/ns/1.0` (P5, unchanged since P5 release)

---

## Open Questions

1. **Where does the TIFF input folder path come from for `<surface @facs>`?**
   - What we know: CONTEXT.md says `facs="../scans/scan_001.tif"` — a relative path to input folder
   - What's unclear: The actual input folder path is configured via `--input` CLI flag; `app.config` may or may not store it. Looking at app.py, there is an `UPLOAD_SUBDIR` constant and uploads go to `output/uploads/`. The TIFF path relative to `output/tei/` would be `../uploads/<stem>.tif` if the file was uploaded, not `../scans/<stem>.tif`.
   - Recommendation: Use `../uploads/<stem>.tif` as the default `facs` path on `<surface>` (since all files are uploaded to `output/uploads/`). This matches the actual file location. The CONTEXT.md example `../scans/` is illustrative, not prescriptive.

2. **Column sort and hyphen rejoin must be re-implemented in Python — complexity risk**
   - What we know: The logic exists in viewer.html JavaScript; it's ~60 lines of column clustering and hyphen detection
   - What's unclear: Edge cases differ between display (frontend) and export (backend) — the export version does not need to match pixel-perfect to the display, but should produce the same reading order
   - Recommendation: Port `columnSort()` and `rejoinHyphens()` from viewer.html into `tei.py` with the same algorithm (HPOS clustering gap = 20% page_width, full-width threshold = 60%). Keep it as private functions `_column_sort()` and `_rejoin_hyphens()`.

3. **Struct role assignment for TEI `<div type="...">` — which source drives this?**
   - What we know: In the frontend, roles come from VLM region `type` → `VLM_TYPE_TO_ROLE` mapping. In TEI, `<div type="article">` wraps each VLM region. The `type` attribute on the TEI div should reflect the VLM region type.
   - What's unclear: VLM region types are `headline`, `article`, `advertisement`, `illustration`, `caption`. TEI uses `article`, `heading`, `advertisement` as `div @type` values (no standard vocabulary constraint from TEI P5 itself).
   - Recommendation: Map VLM region types directly: `headline` → `div type="heading"`, `article` → `div type="article"`, `advertisement` → `div type="advertisement"`, `illustration` → `div type="figure"`, `caption` → `div type="caption"`. This is Claude's discretion per CONTEXT.md.

---

## Sources

### Primary (HIGH confidence)
- https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-pb.html — `<pb>` element spec, `facs` attribute, v4.11.0
- https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-surface.html — `<surface>` element spec, `xml:id`, coordinate attributes
- https://www.tei-c.org/release/doc/tei-p5-doc/en/html/ref-zone.html — `<zone>` element spec, `ulx/uly/lrx/lry` attributes
- https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-lb.html — `<lb/>` element spec, placement convention, `break` attribute
- https://tei-c.org/release/doc/tei-p5-doc/en/html/examples-teiHeader.html — teiHeader examples including encodingDesc
- lxml 5.3.0 (in project) — verified namespace handling, mixed content, xml:id generation
- `mets.py` (project source) — verified download endpoint and ALTO parsing patterns
- `app.py` `serve_alto()` (project source) — verified `line_end` flag, lxml proxy recycling fix, block data shape
- `templates/viewer.html` (project source) — verified column sort algorithm, hyphen rejoin logic, struct role assignment

### Secondary (MEDIUM confidence)
- https://www.tei-c.org/release/doc/tei-p5-doc/en/html/PH.html — facsimile integration patterns (fetched, verified against spec)
- https://tei-c.org/release/doc/tei-p5-doc/en/html/DS.html — default text structure including `<div type>` usage

### Tertiary (LOW confidence)
- WebSearch result: "TEI P5 Version 4.11.0 last updated 18th February 2026" — confirms currency of spec; not independently verified via changelog

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — lxml and Flask already in project; no new dependencies
- Architecture: HIGH — TEI P5 spec confirmed from official docs; patterns verified against existing project code
- Pitfalls: HIGH — most pitfalls are documented in project accumulated context (proxy recycling, JPEG vs ALTO coords, hash prefix)
- Open questions: MEDIUM — TIFF path question is answerable from code inspection; column sort port is mechanical

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (TEI P5 spec is stable; lxml API is stable)
