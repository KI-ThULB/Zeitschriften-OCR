# Phase 21: TEI P5 Export - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate a TEI P5 XML document for the currently loaded page in the viewer — one TEI per TIFF, on demand. The document encodes article structure derived from VLM segmentation, normalized text (column-sorted, hyphens rejoined), line boundaries (`<lb/>`), and facsimile coordinates for each article region. A "Download TEI" button in the top toolbar triggers the export. Generated files are saved to `output/tei/<stem>.xml` and also served as a browser download.

</domain>

<decisions>
## Implementation Decisions

### Export scope and trigger
- **Unit:** Single page — one TEI document per currently loaded TIFF file
- **Trigger:** "Download TEI" button in the top toolbar header area of the viewer (alongside file name / existing page-level controls)
- **Output saved to disk:** `output/tei/<stem>.xml` — alongside `output/alto/` and `output/mets/`
- **Also served as HTTP response:** Browser download triggered by the same Flask endpoint that writes the file
- **No VLM data for page:** Export proceeds anyway; XML comment inserted noting VLM data was absent; all text rendered as one `<div type="article">` with paragraph role

### Text content
- **Word source:** Normalized display words — column-sorted (left-to-right reading order), hyphens rejoined (e.g. "Verbindung" not "Ver-" + "bindung")
- **Source of truth:** ALTO XML on disk — corrections saved via the editor are already written back to ALTO, so reading from disk captures them automatically
- **Low-confidence words:** Plain text, no special TEI annotation (no `<unclear>`, no `@cert`)
- **`<lb/>` placement:** Inserted after each line-terminal word; for rejoined hyphenated words, `<lb/>` appears after the rejoined form (e.g. `Verbindung<lb/>`)

### TEI header and metadata
- **Header source:** METS/MODS file at `output/mets/<stem>_mets.xml` if it exists; fall back to filename-derived title if absent
- **MODS fields to populate:** title + date + publisher/source (three fields); skip any field not present in MODS
- **encodingDesc:** Short boilerplate — tool name ("Zeitschriften-OCR") and generation date; no elaborate schema description

### Facsimile and coordinate system
- **`<facsimile>` section:** One `<surface xml:id="page-{stem}">` per page; one `<zone>` per VLM article region
- **Zone coordinates:** ALTO pixel space — `ulx`, `uly`, `lrx`, `lry` attributes (VLM 0.0–1.0 fractional coords × pageWidth/pageHeight)
- **`<surface @facs>`:** Relative path to the TIFF in the input folder (e.g. `../scans/scan_001.tif`)

### Edge case: no VLM data
- `<body>` contains one `<div type="article">` wrapping all detected paragraphs
- An XML comment is added at the top of `<body>`: `<!-- VLM segmentation absent: all text rendered as single article -->`
- No `<zone>` elements in `<facsimile>` when no VLM data; `<surface>` element still present

### Claude's Discretion
- Exact Flask endpoint path for the download (e.g. `/tei/<stem>` or `/export/tei/<stem>`)
- Whether to add a `<revisionDesc>` in teiHeader or leave it out
- Exact `<encodingDesc>` wording and element structure
- How `<pb>` is placed relative to `<body>` (before first word of page, or as a milestone element)
- METS parsing strategy (which XPath or namespace to use for MODS fields)

</decisions>

<specifics>
## Specific Ideas

- The "Download TEI" button lives in the top toolbar — same row as the current file name display; consistent with page-level actions
- TEI file saved to `output/tei/` so it persists across sessions and can be found by other tools alongside the ALTO and METS output
- Flask endpoint writes the file then returns it as `Content-Disposition: attachment` so the browser saves it automatically
- The METS file naming convention from Phase 16 is `output/mets/<stem>_mets.xml` — the TEI generator reads from that path

</specifics>

<deferred>
## Deferred Ideas

- `<choice><orig>Ver-</orig><reg>Verbindung</reg></choice>` elements for rejoined hyphens — TEI-04 in future requirements
- Per-article TEI export (TEI-05) — future phase
- Multi-page issue TEI combining all pages — future milestone
- `@cert` annotation for low-confidence words — out of scope for this phase

</deferred>

---

*Phase: 21-tei-p5-export*
*Context gathered: 2026-03-03*
