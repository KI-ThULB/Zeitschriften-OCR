---
phase: 01-single-file-pipeline
verified: 2026-02-24T18:00:00Z
status: gaps_found
score: 10/11 must-haves verified
gaps:
  - truth: "xsi:schemaLocation is removed from output — no contradictory ALTO 3 XSD reference"
    status: failed
    reason: |
      build_alto21() Step 5 attempts to strip the xsi:schemaLocation pointing to the ALTO 3.0 XSD,
      but it targets the string 'xsi:schemaLocation="http://www.loc.gov/standards/alto/ns-v3# ...'
      which no longer exists at Step 5 because Step 4 already replaced ALTO3_NS with ALTO21_NS
      throughout the serialised string. The replace() call silently no-ops. The output file
      retains xsi:schemaLocation="http://schema.ccs-gmbh.com/ALTO http://www.loc.gov/alto/v3/alto-3-0.xsd"
      — pointing to the ALTO 3.0 XSD under the ALTO 2.1 namespace key — a contradictory
      schema reference that prevents strict schema validation.
    artifacts:
      - path: "pipeline.py"
        issue: |
          build_alto21() Step 5 strip target 'http://www.loc.gov/standards/alto/ns-v3#' does not
          match the post-Step-4 string 'http://schema.ccs-gmbh.com/ALTO'. Strip must target
          'alto-3-0.xsd' (invariant part) or run before the namespace replace, or use a regex.
      - path: "output/alto/144528908_0019.xml"
        issue: |
          File contains xsi:schemaLocation="http://schema.ccs-gmbh.com/ALTO
          http://www.loc.gov/alto/v3/alto-3-0.xsd" — the ALTO 2.1 namespace key maps to the
          ALTO 3.0 XSD. An lxml XSD validator will reject this or follow the wrong schema.
    missing:
      - "Fix Step 5 in build_alto21() to strip schemaLocation BEFORE Step 4 (namespace replace),
         OR change the target string to match the post-Step-4 form, OR strip any xsi:schemaLocation
         attribute on the root element via lxml before serialising."
human_verification:
  - test: "Validate output/alto/144528908_0019.xml against the official ALTO 2.1 XSD"
    expected: "lxml validates without errors after the schemaLocation bug is fixed"
    why_human: "ALTO 2.1 XSD download URL must be confirmed; machine cannot resolve external schema"
---

# Phase 01: Single-File Pipeline Verification Report

**Phase Goal:** A single TIFF can be processed to a schema-valid ALTO 2.1 file with correct DPI,
correct namespace, and word coordinates that align with the original uncropped TIFF
**Verified:** 2026-02-24T18:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                 | Status     | Evidence                                                                          |
|----|-----------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------|
| 1  | load_tiff() returns (image, dpi_tuple, warnings) 3-tuple             | VERIFIED   | Signature correct; `img.info.get('dpi')` present; fallback (300.0, 300.0) + 'no DPI tag, using 300' warning confirmed |
| 2  | load_tiff() appends 'no DPI tag, using 300' when DPI absent          | VERIFIED   | Source: `warnings.append('no DPI tag, using 300')` on line 55                    |
| 3  | detect_crop_box() uses THRESH_BINARY (not THRESH_BINARY_INV)         | VERIFIED   | Source: `cv2.THRESH_BINARY + cv2.THRESH_OTSU`; 'THRESH_BINARY_INV' absent        |
| 4  | detect_crop_box() ratio fallback returns full bounds + fallback=True | VERIFIED   | `if not (min_ratio <= ratio <= max_ratio): return (0, 0, img_w, img_h), True`    |
| 5  | --no-crop bypasses detection, uses full image bounds                 | VERIFIED   | `crop_box = (0, 0, img.size[0], img.size[1])` when `no_crop=True`                |
| 6  | run_ocr() calls pytesseract.image_to_alto_xml with --dpi flag        | VERIFIED   | `pytesseract.image_to_alto_xml(image, lang=lang, config=config)` confirmed        |
| 7  | ALTO root element has xmlns='http://schema.ccs-gmbh.com/ALTO'        | VERIFIED   | output/alto/144528908_0019.xml root namespace confirmed; no ns-v3 remnant         |
| 8  | HPOS/VPOS offset by crop_box[0]/crop_box[1]; WIDTH/HEIGHT untouched  | VERIFIED   | crop_y=72; PrintSpace VPOS=72 in output; WIDTH/HEIGHT never written in source     |
| 9  | End-to-end run exits 0 and prints one result line to stdout          | VERIFIED   | Confirmed in 01-02-SUMMARY: 46 words, exit 0                                      |
| 10 | Output path follows output_dir/alto/{stem}.xml convention            | VERIFIED   | `out_path = output_dir / 'alto' / (tiff_path.stem + '.xml')` confirmed           |
| 11 | xsi:schemaLocation removed — no contradictory ALTO 3 XSD reference  | FAILED     | Step 5 strip targets ALTO3_NS string, but Step 4 already replaced it; strip silently no-ops; output retains `xsi:schemaLocation="http://schema.ccs-gmbh.com/ALTO http://www.loc.gov/alto/v3/alto-3-0.xsd"` |

**Score:** 10/11 truths verified

---

### Required Artifacts

| Artifact                              | Provides                                      | Status   | Details                                              |
|---------------------------------------|-----------------------------------------------|----------|------------------------------------------------------|
| `requirements.txt`                    | Pinned library versions for reproducibility   | VERIFIED | Pillow>=11.1.0, opencv-python-headless>=4.9.0, pytesseract>=0.3.13, lxml>=5.3.0; all four import successfully |
| `pipeline.py`                         | Complete five-function pipeline               | VERIFIED | 308 lines (above 160-line minimum); load_tiff, detect_crop_box, run_ocr, build_alto21, count_words, process_tiff, main all present and substantive |
| `output/alto/144528908_0019.xml`      | Actual ALTO output on real Zeitschriften TIFF | PARTIAL  | Exists with correct namespace and 46 words; but xsi:schemaLocation still references ALTO 3.0 XSD (see gap) |

---

### Key Link Verification

| From                          | To                                | Via                                    | Status  | Details                                                                 |
|-------------------------------|-----------------------------------|----------------------------------------|---------|-------------------------------------------------------------------------|
| pipeline.py load_tiff()       | image.info.get('dpi')             | Pillow TIFF metadata tag               | WIRED   | `img.info.get('dpi')` present in load_tiff source                      |
| pipeline.py detect_crop_box() | cv2.THRESH_BINARY                 | OpenCV threshold                       | WIRED   | `cv2.THRESH_BINARY + cv2.THRESH_OTSU` confirmed; INV absent            |
| pipeline.py run_ocr()         | pytesseract.image_to_alto_xml()   | direct call with --dpi config flag     | WIRED   | `image_to_alto_xml` called with `config=f'--psm {psm} --dpi {dpi}'`   |
| pipeline.py build_alto21()    | ALTO3_NS -> ALTO21_NS string replace | lxml tostring + str.replace + re-parse | WIRED   | `xml_str.replace(ALTO3_NS, ALTO21_NS)` confirmed                       |
| pipeline.py build_alto21()    | HPOS/VPOS offset before ns rewrite | lxml element iteration on ALTO3 namespace | WIRED | Offset in Step 2 (ALTO3 namespace), replace in Step 4 — correct order  |
| pipeline.py build_alto21()    | xsi:schemaLocation removal        | Step 5 str.replace                    | BROKEN  | Step 5 targets original ALTO3_NS in schemaLocation key, but Step 4 already replaced it; strip silently fails |
| pipeline.py process_tiff()    | output_dir/'alto'/(stem+'.xml')   | pathlib Path construction              | WIRED   | `out_path = output_dir / 'alto' / (tiff_path.stem + '.xml')` confirmed |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                 | Status    | Evidence                                                                              |
|-------------|-------------|---------------------------------------------------------------------------------------------|-----------|---------------------------------------------------------------------------------------|
| PIPE-01     | 01-01-PLAN  | Pillow lazy load + DPI extraction; fallback to 300 with warning                             | SATISFIED | load_tiff() confirmed: lazy open, `img.info.get('dpi')`, fallback (300.0, 300.0), warning accumulation |
| PIPE-02     | 01-01-PLAN  | OpenCV contour crop; configurable padding (default 50px); fallback if area <40% or >98%    | SATISFIED | detect_crop_box() confirmed: THRESH_BINARY, padding clamping, min/max ratio fallback  |
| PIPE-03     | 01-02-PLAN  | Tesseract 5.x LSTM on cropped image with configurable --lang and --psm                     | SATISFIED | run_ocr() confirmed: `image_to_alto_xml` with `--psm {psm} --dpi {dpi}`, lang passed |
| PIPE-04     | 01-02-PLAN  | Schema-valid ALTO 2.1 XML; namespace corrected to CCS-GmbH; HPOS += crop_x, VPOS += crop_y | PARTIAL   | Namespace correct, coordinates verified. But schema validity is compromised: xsi:schemaLocation still references ALTO 3.0 XSD (alto-3-0.xsd) under the ALTO 2.1 namespace key. An XSD validator following that reference will use the wrong schema. |

**PIPE-04 is partially satisfied.** The namespace, coordinate offset, and structural content are correct. The schema-validity aspect has a gap: the output file contains a contradictory `xsi:schemaLocation` that undermines the "schema-valid" claim in the requirement.

No orphaned requirements — all four PIPE-01 through PIPE-04 requirements mapped to Phase 1 plans are accounted for.

---

### Anti-Patterns Found

| File        | Line | Pattern                          | Severity | Impact                                                    |
|-------------|------|----------------------------------|----------|-----------------------------------------------------------|
| pipeline.py | 179  | Step 5 strip target already mutated by Step 4 | Warning | xsi:schemaLocation pointing to ALTO 3.0 XSD persists in output; schema validation will use wrong XSD |

No TODO/FIXME/PLACEHOLDER comments, no empty return stubs, no console.log patterns found.

---

### Human Verification Required

#### 1. ALTO 2.1 Schema Validation

**Test:** After the schemaLocation bug is fixed, validate `output/alto/144528908_0019.xml` against the official ALTO 2.1 XSD (download from `http://schema.ccs-gmbh.com/ALTO/alto-2-1.xsd` or the Library of Congress mirror).
**Expected:** Zero XSD validation errors.
**Why human:** The ALTO 2.1 XSD URL requires an external network request to confirm the current schema; automated check without the XSD file cannot validate structurally.

---

### Gap Detail

#### Gap: xsi:schemaLocation Not Stripped (Step 5 Bug in build_alto21)

**Root cause:** `build_alto21()` Step 4 replaces `ALTO3_NS` with `ALTO21_NS` in the entire serialised string. At Step 5, the code then tries to remove:

```
xsi:schemaLocation="http://www.loc.gov/standards/alto/ns-v3# http://www.loc.gov/alto/v3/alto-3-0.xsd"
```

But Step 4 already replaced `http://www.loc.gov/standards/alto/ns-v3#` with `http://schema.ccs-gmbh.com/ALTO` — so the target string is:

```
xsi:schemaLocation="http://schema.ccs-gmbh.com/ALTO http://www.loc.gov/alto/v3/alto-3-0.xsd"
```

The `str.replace()` call finds no match and silently returns the string unchanged. The ALTO output file retains the contradictory schema reference.

**Impact on PIPE-04:** The requirement specifies "schema-valid ALTO 2.1 XML". An XML validator told to use `xsi:schemaLocation` will attempt to validate against `alto-3-0.xsd` (the ALTO 3.0 schema), which will either fail outright or validate against the wrong contract. This is a known risk flagged in the 01-02-PLAN.md (Step 5 comment) but the fix did not account for the ordering dependency.

**Fix options (in order of simplicity):**

1. Move Step 5 to run before Step 4 (strip schemaLocation from the serialised ALTO3 string before namespace replacement).
2. Change Step 5 target string to match the post-Step-4 form: `'xsi:schemaLocation="http://schema.ccs-gmbh.com/ALTO http://www.loc.gov/alto/v3/alto-3-0.xsd"'`.
3. Use lxml to remove the `xsi:schemaLocation` attribute from the `root` element before serialising (cleanest approach: `root.attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', None)` after Step 1, before Step 3).

---

_Verified: 2026-02-24T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
