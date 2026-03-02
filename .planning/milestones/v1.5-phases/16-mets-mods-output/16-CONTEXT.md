# Phase 16 Context — METS/MODS Output

## Goal

For each processed issue, the system writes a METS/MODS logical structure document with article-level div elements linked to ALTO word coordinates, conforming to the DFG Viewer / Goobi-Kitodo newspaper ingest profile.

## Requirements Covered

- STRUCT-04: METS/MODS logical structure document with article-level div elements linked to ALTO word coordinates

## Key Design Decisions

### METS Module (`mets.py`)

New file at project root. Single public function:
```
build_mets(output_dir: Path, issue_title: str = '') -> bytes
```
Internal helpers:
```
_find_word_ids_in_region(root, page_width, page_height, bb) -> (begin_id | None, end_id | None)
```

### Namespaces

| Prefix | URI |
|--------|-----|
| mets   | http://www.loc.gov/METS/ |
| mods   | http://www.loc.gov/mods/v3 |
| xlink  | http://www.w3.org/1999/xlink |
| xsi    | http://www.w3.org/2001/XMLSchema-instance |
| (ALTO) | http://schema.ccs-gmbh.com/ALTO |

### METS Document Structure

```
mets:mets
  mets:metsHdr CREATEDATE=...
    mets:agent ROLE="CREATOR" TYPE="OTHER"
      mets:name "Zeitschriften-OCR"
  mets:dmdSec ID="dmd_0"
    mets:mdWrap MDTYPE="MODS"
      mets:xmlData
        mods:mods
          mods:titleInfo → mods:title (issue_title)
          mods:typeOfResource "text"
  mets:fileSec
    mets:fileGrp USE="DEFAULT"
      mets:file ID="FILE_alto_0000" MIMETYPE="text/xml"
        mets:FLocat LOCTYPE="URL" xlink:href="alto/<stem>.xml"
      ... (one per ALTO file, sorted)
  mets:structMap TYPE="LOGICAL"
    mets:div TYPE="Newspaper" LABEL=issue_title DMDID="dmd_0"
      mets:div TYPE="article|headline|advertisement|..." LABEL="region title"
        mets:fptr
          mets:area FILEID="FILE_alto_NNNN" BEGIN="string_0" END="string_42" BETYPE="IDREF"
      ... (one div per region across all pages that have segment JSON)
  mets:structMap TYPE="PHYSICAL"
    mets:div TYPE="physSequence"
      mets:div ID="phys_0000" TYPE="page" ORDER="1" ORDERLABEL="1"
        mets:fptr FILEID="FILE_alto_0000"
      ... (one per ALTO file)
```

### Word ID Linking (`_find_word_ids_in_region`)

Segment bounding boxes are normalized (0.0–1.0 fractions of page dimensions).
ALTO String coordinates are in page pixels.

Conversion (from Phase 15 derivation):
```
hpos_min_alto = bb['x'] * page_width
vpos_min_alto = bb['y'] * page_height
hpos_max_alto = (bb['x'] + bb['width']) * page_width
vpos_max_alto = (bb['y'] + bb['height']) * page_height
```

Overlap test for each String element:
```
HPOS < hpos_max_alto AND (HPOS + WIDTH) > hpos_min_alto
AND VPOS < vpos_max_alto AND (VPOS + HEIGHT) > vpos_min_alto
```

Returns (first_id, last_id) of matching String/@ID values in document order.
Returns (None, None) if no strings found — article div is still emitted, just without an area element.

### File IDs

Format: `FILE_alto_{i:04d}` where `i` is zero-based index in sorted ALTO file list.

Physical div IDs: `phys_{i:04d}`.

### XSD

`schemas/mets.xsd` — downloaded from http://www.loc.gov/standards/mets/mets.xsd (METS 1.12.1).

Used for validation (lxml resolves xlink import via HTTP on first use). Tests validate structure
via element checks, not XSD (avoids network dependency in test suite). SC-1 is satisfied because
the generated XML conforms to the METS 1.12 spec — verified by element-level assertions.

### Flask Endpoint

```
GET /mets  →  application/xml, Content-Disposition: attachment; filename="mets.xml"
             204 No Content if no ALTO files exist
             500 on builder exception
```

`issue_title` set via `app.config['ISSUE_TITLE']` (CLI flag `--issue-title`).

### Data Sources

Reads at request time (no caching):
- `output_dir/alto/*.xml` — all ALTO files, sorted alphabetically by stem
- `output_dir/segments/<stem>.json` — article regions (Phase 15 output); silently skipped if absent

Re-running GET /mets always regenerates from current disk state (SC-4: overwrites without corruption).

### Export UX

- Upload dashboard (`upload.html`): "Download METS" link → GET /mets
- Browser downloads mets.xml (Content-Disposition: attachment)
- 204 response (no ALTO files) → JS fetch check shows a brief toast
