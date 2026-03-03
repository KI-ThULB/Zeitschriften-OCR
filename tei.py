"""tei.py — TEI P5 XML builder for Zeitschriften-OCR.

Reads:
  output_dir/alto/<stem>.xml       — ALTO 2.1 (CCS-GmbH namespace)
  output_dir/segments/<stem>.json  — VLM article regions (optional; fallback if absent)

Returns UTF-8 TEI P5 XML bytes suitable for scholarly ingest and DFG viewer use.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

from pipeline import ALTO21_NS  # 'http://schema.ccs-gmbh.com/ALTO'

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

TEI_NS  = 'http://www.tei-c.org/ns/1.0'
XML_NS  = 'http://www.w3.org/XML/1998/namespace'
MODS_NS = 'http://www.loc.gov/mods/v3'

_NSMAP = {None: TEI_NS}


def _t(tag: str) -> str:
    """Return Clark-notation tag in TEI namespace."""
    return f'{{{TEI_NS}}}{tag}'


def _xml_id(val: str) -> str:
    """Return Clark-notation xml:id key."""
    return f'{{{XML_NS}}}id'


# ---------------------------------------------------------------------------
# MODS metadata reader
# ---------------------------------------------------------------------------

def _read_mods_metadata(output_dir: Path, stem: str) -> dict:
    """Read title/date/publisher from per-stem METS file if present.

    Falls back to empty values when the file does not exist (the common case,
    since mets.py generates XML on demand and does not write per-stem files).
    """
    mets_path = output_dir / 'mets' / (stem + '_mets.xml')
    result: dict = {'title': None, 'date': None, 'publisher': None}
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


# ---------------------------------------------------------------------------
# Column sort
# ---------------------------------------------------------------------------

def _column_sort(words: list[dict], page_width: int) -> list[dict]:
    """Sort words in multi-column reading order.

    Groups TextBlocks by HPOS clustering (gap > 20% page_width separates
    columns).  Full-width blocks (WIDTH > 60% page_width) sort first (column
    index -1).  Within each column: ascending block VPOS, then word VPOS,
    then word HPOS.

    Each word dict must contain: content, hpos, vpos, width, height,
    line_end, block_hpos, block_width, block_vpos.
    """
    if not words:
        return words

    gap_threshold = 0.2 * page_width
    full_width_threshold = 0.6 * page_width

    # Collect unique (block_hpos, block_width, block_vpos) tuples
    block_keys: list[tuple[float, float, float]] = []
    seen: set[tuple[float, float, float]] = set()
    for w in words:
        key = (w['block_hpos'], w['block_width'], w['block_vpos'])
        if key not in seen:
            seen.add(key)
            block_keys.append(key)

    # Sort block keys by HPOS so we can detect column gaps
    block_keys.sort(key=lambda b: b[0])

    # Assign column index to each block key
    col_index: dict[tuple[float, float, float], int] = {}
    current_col = 0
    prev_hpos: float | None = None
    for key in block_keys:
        bh, bw, bv = key
        if bw > full_width_threshold:
            col_index[key] = -1  # full-width: sorts first
            prev_hpos = None     # reset gap detection after full-width block
            continue
        if prev_hpos is not None and (bh - prev_hpos) > gap_threshold:
            current_col += 1
        col_index[key] = current_col
        prev_hpos = bh

    def _sort_key(w: dict) -> tuple:
        bkey = (w['block_hpos'], w['block_width'], w['block_vpos'])
        ci = col_index.get(bkey, 0)
        return (ci, w['block_vpos'], w['vpos'], w['hpos'])

    return sorted(words, key=_sort_key)


# ---------------------------------------------------------------------------
# Hyphen rejoin
# ---------------------------------------------------------------------------

def _rejoin_hyphens(words: list[dict]) -> list[dict]:
    """Merge end-of-line hyphenated word pairs.

    If a word ends with '-' and has line_end=True, it is concatenated with the
    next word (hyphen stripped).  The merged word inherits line_end=False so
    the intermediate <lb/> is suppressed.
    """
    result: list[dict] = []
    i = 0
    while i < len(words):
        word = words[i]
        if word['content'].rstrip().endswith('-') and word['line_end'] and i + 1 < len(words):
            next_word = words[i + 1]
            merged_content = word['content'].rstrip()[:-1] + next_word['content']
            merged = dict(word)
            merged['content'] = merged_content
            merged['line_end'] = next_word['line_end']  # inherit final line_end state
            result.append(merged)
            i += 2  # consume both words
        else:
            result.append(word)
            i += 1
    return result


# ---------------------------------------------------------------------------
# Word-to-region assignment
# ---------------------------------------------------------------------------

def _assign_word_to_region(
    hpos: float,
    vpos: float,
    w: float,
    h: float,
    regions: list[dict],
    page_width: int,
    page_height: int,
) -> str | None:
    """Return the id of the first region whose pixel bbox overlaps the word.

    Uses the same intersection test as mets._find_word_ids_in_region().
    Returns None if no region overlaps.
    """
    for region in regions:
        bb = region.get('bounding_box', {})
        if not bb:
            continue
        hpos_min = bb['x'] * page_width
        vpos_min = bb['y'] * page_height
        hpos_max = (bb['x'] + bb['width']) * page_width
        vpos_max = (bb['y'] + bb['height']) * page_height
        if (hpos < hpos_max and (hpos + w) > hpos_min
                and vpos < vpos_max and (vpos + h) > vpos_min):
            return region['id']
    return None


# ---------------------------------------------------------------------------
# Mixed-content <p> builder
# ---------------------------------------------------------------------------

def _build_paragraph(parent: etree._Element, words_in_group: list[dict]) -> None:
    """Append a <p> element with words and inter-line <lb/> milestones to parent.

    Rules:
    - Words are space-joined within a line.
    - After each line boundary (line_end=True) that is NOT the last word in the
      group, flush accumulated text and insert an <lb/> milestone.
    - No trailing <lb/> after the last word.
    """
    if not words_in_group:
        return

    p_elem = etree.SubElement(parent, _t('p'))
    pending: list[str] = []

    def _flush(elem: etree._Element, text: str) -> None:
        """Append text to elem.text or last-child.tail."""
        if len(elem) == 0:
            elem.text = (elem.text or '') + text
        else:
            elem[-1].tail = (elem[-1].tail or '') + text

    for idx, word in enumerate(words_in_group):
        is_last = (idx == len(words_in_group) - 1)
        pending.append(word['content'])

        if word['line_end'] and not is_last:
            # Flush accumulated words then insert <lb/>
            segment = ' '.join(pending)
            _flush(p_elem, segment)
            lb = etree.SubElement(p_elem, _t('lb'))
            lb.tail = ''
            pending = []

    # Flush remaining text (no trailing lb)
    if pending:
        _flush(p_elem, ' '.join(pending))


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_tei(output_dir: Path, stem: str) -> bytes:
    """Build a TEI P5 document for one page from ALTO XML and VLM segment data.

    Args:
        output_dir: Root output directory (contains alto/, segments/ subdirs).
        stem: Filename stem (without extension) of the ALTO/TIFF file.

    Returns:
        UTF-8 encoded TEI P5 XML bytes beginning with the XML declaration.
    """
    output_dir = Path(output_dir)
    alto_path = output_dir / 'alto' / (stem + '.xml')

    # ------------------------------------------------------------------
    # Parse ALTO
    # ------------------------------------------------------------------
    alto_root = etree.parse(str(alto_path)).getroot()

    alto_page = alto_root.find(f'.//{{{ALTO21_NS}}}Page')
    page_width  = int(alto_page.get('WIDTH', 0))  if alto_page is not None else 0
    page_height = int(alto_page.get('HEIGHT', 0)) if alto_page is not None else 0

    # Materialise once — avoid lxml proxy recycling (Phase 19-01 pattern)
    all_strings   = list(alto_root.iter(f'{{{ALTO21_NS}}}String'))
    all_textlines = list(alto_root.iter(f'{{{ALTO21_NS}}}TextLine'))
    all_blocks    = list(alto_root.iter(f'{{{ALTO21_NS}}}TextBlock'))

    # Build line_end set using (CONTENT, HPOS, VPOS) tuples
    line_end_set: set[tuple[str, str, str]] = set()
    for tl in all_textlines:
        strings_in_line = [c for c in tl if c.tag == f'{{{ALTO21_NS}}}String']
        if strings_in_line:
            last = strings_in_line[-1]
            line_end_set.add((
                last.get('CONTENT', ''),
                last.get('HPOS', ''),
                last.get('VPOS', ''),
            ))

    # Build string→block mapping
    string_to_block: dict[str, etree._Element] = {}
    for block in all_blocks:
        for s in block.iter(f'{{{ALTO21_NS}}}String'):
            # key by element id() is unsafe due to proxy recycling;
            # use (CONTENT,HPOS,VPOS) tuple instead
            key = (s.get('CONTENT', ''), s.get('HPOS', ''), s.get('VPOS', ''))
            string_to_block[str(id(s))] = block

    # Build block HPOS/VPOS/WIDTH lookup by block id
    block_by_id: dict[str, etree._Element] = {
        b.get('ID', ''): b for b in all_blocks
    }

    # Build string list with metadata
    raw_words: list[dict] = []
    for s in all_strings:
        s_key = (s.get('CONTENT', ''), s.get('HPOS', ''), s.get('VPOS', ''))
        is_line_end = s_key in line_end_set

        # Find parent block
        parent_block = string_to_block.get(str(id(s)))
        if parent_block is None:
            # Fallback: walk by spatial containment is expensive; use zeros
            block_hpos = 0.0
            block_vpos = 0.0
            block_width = float(page_width)
        else:
            block_hpos  = float(parent_block.get('HPOS', 0))
            block_vpos  = float(parent_block.get('VPOS', 0))
            block_width = float(parent_block.get('WIDTH', page_width))

        raw_words.append({
            'content':     s.get('CONTENT', ''),
            'hpos':        float(s.get('HPOS', 0)),
            'vpos':        float(s.get('VPOS', 0)),
            'width':       float(s.get('WIDTH', 0)),
            'height':      float(s.get('HEIGHT', 0)),
            'line_end':    is_line_end,
            'block_hpos':  block_hpos,
            'block_vpos':  block_vpos,
            'block_width': block_width,
        })

    # Column sort then hyphen rejoin
    sorted_words = _column_sort(raw_words, page_width)
    words        = _rejoin_hyphens(sorted_words)

    # ------------------------------------------------------------------
    # Load VLM segment data
    # ------------------------------------------------------------------
    seg_path = output_dir / 'segments' / (stem + '.json')
    regions: list[dict] = []
    if seg_path.exists():
        try:
            seg_data = json.loads(seg_path.read_text())
            regions = seg_data.get('regions', []) or []
        except Exception:
            regions = []

    # ------------------------------------------------------------------
    # Assign words to regions
    # ------------------------------------------------------------------
    # region_id -> list of word dicts
    region_words: dict[str | None, list[dict]] = {r['id']: [] for r in regions}
    region_words[None] = []  # fallback bucket

    for word in words:
        rid = _assign_word_to_region(
            word['hpos'], word['vpos'],
            word['width'], word['height'],
            regions, page_width, page_height,
        )
        if rid is not None and rid in region_words:
            region_words[rid].append(word)
        else:
            region_words[None].append(word)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    meta = _read_mods_metadata(output_dir, stem)
    title_text  = meta['title'] or stem
    date_text   = meta['date'] or ''
    pub_text    = meta['publisher'] or ''
    today_iso   = datetime.now(timezone.utc).date().isoformat()

    # ------------------------------------------------------------------
    # Build lxml tree
    # ------------------------------------------------------------------
    root = etree.Element(_t('TEI'), nsmap=_NSMAP)

    # --- teiHeader ---
    header = etree.SubElement(root, _t('teiHeader'))
    file_desc = etree.SubElement(header, _t('fileDesc'))

    title_stmt = etree.SubElement(file_desc, _t('titleStmt'))
    etree.SubElement(title_stmt, _t('title')).text = title_text

    pub_stmt = etree.SubElement(file_desc, _t('publicationStmt'))
    pub_p = etree.SubElement(pub_stmt, _t('p'))
    pub_p.text = pub_text if pub_text else 'Generated by Zeitschriften-OCR'

    source_desc = etree.SubElement(file_desc, _t('sourceDesc'))
    src_p = etree.SubElement(source_desc, _t('p'))
    src_p.text = f'OCR output: {stem}.tif' + (f'; date: {date_text}' if date_text else '')

    enc_desc = etree.SubElement(header, _t('encodingDesc'))
    proj_desc = etree.SubElement(enc_desc, _t('projectDesc'))
    etree.SubElement(proj_desc, _t('p')).text = (
        f'Generated by Zeitschriften-OCR on {today_iso}'
    )

    # --- facsimile ---
    facs_elem = etree.SubElement(root, _t('facsimile'))
    surface = etree.SubElement(
        facs_elem, _t('surface'),
        **{_xml_id('surface'): f'page-{stem}'},
        ulx='0', uly='0',
        lrx=str(page_width),
        lry=str(page_height),
        facs=f'../uploads/{stem}.tif',
    )

    for region in regions:
        bb = region.get('bounding_box', {})
        if bb:
            ulx = int(bb['x'] * page_width)
            uly = int(bb['y'] * page_height)
            lrx = int((bb['x'] + bb['width']) * page_width)
            lry = int((bb['y'] + bb['height']) * page_height)
            etree.SubElement(
                surface, _t('zone'),
                **{_xml_id('zone'): f'zone-{stem}-{region["id"]}'},
                ulx=str(ulx), uly=str(uly),
                lrx=str(lrx), lry=str(lry),
                type=region.get('type', 'article'),
            )

    # --- text/body ---
    text_elem = etree.SubElement(root, _t('text'))
    body = etree.SubElement(text_elem, _t('body'))

    if not regions:
        # No VLM data: insert comment then single fallback div
        body.append(etree.Comment(
            ' VLM segmentation absent: all text rendered as single article '
        ))
        fallback_div = etree.SubElement(body, _t('div'), type='article', n='1')
        pb = etree.SubElement(fallback_div, _t('pb'), n='1', facs=f'#page-{stem}')
        fallback_words = words  # all words go into fallback
        # Group into a single paragraph (simple: all words as one block)
        _build_paragraph(fallback_div, fallback_words)
    else:
        # One <div type="article"> per region
        pb = etree.SubElement(body, _t('pb'), n='1', facs=f'#page-{stem}')
        for i, region in enumerate(regions):
            div = etree.SubElement(body, _t('div'), type='article', n=str(i + 1))
            if region.get('title'):
                etree.SubElement(div, _t('head')).text = region['title']
            # All words assigned to this region go into one paragraph
            _build_paragraph(div, region_words.get(region['id'], []))

        # Unassigned words: append to last div or create extra div
        fallback = region_words.get(None, [])
        if fallback:
            last_div = list(body.findall(_t('div')))[-1]
            _build_paragraph(last_div, fallback)

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
