"""mets.py — METS/MODS document builder for DFG Viewer / Goobi-Kitodo newspaper ingest.

Reads:
  output_dir/alto/<stem>.xml  — ALTO 2.1 files (page structure + String IDs for word-level linking)
  output_dir/segments/<stem>.json  — article regions from Phase 15 VLM segmentation

Returns METS 1.12.1 XML bytes conforming to the DFG Viewer newspaper ingest profile.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

METS_NS = 'http://www.loc.gov/METS/'
MODS_NS = 'http://www.loc.gov/mods/v3'
XLINK_NS = 'http://www.w3.org/1999/xlink'
XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO'

_NSMAP = {
    'mets': METS_NS,
    'mods': MODS_NS,
    'xlink': XLINK_NS,
    'xsi': XSI_NS,
}


def _mets(tag: str) -> str:
    return f'{{{METS_NS}}}{tag}'


def _mods(tag: str) -> str:
    return f'{{{MODS_NS}}}{tag}'


# ---------------------------------------------------------------------------
# Word ID lookup
# ---------------------------------------------------------------------------

def _find_word_ids_in_region(
    root: etree._Element,
    page_width: int,
    page_height: int,
    bb: dict,
) -> tuple[str | None, str | None]:
    """Return (first_id, last_id) of ALTO String elements overlapping the bounding box.

    bb: normalized bounding box {x, y, width, height} (0.0–1.0 fractions of page dimensions).
    Converts to ALTO pixel coordinates and iterates String elements in document order.
    Returns (None, None) if no strings found in region — caller omits the area element.
    """
    hpos_min = bb['x'] * page_width
    vpos_min = bb['y'] * page_height
    hpos_max = (bb['x'] + bb['width']) * page_width
    vpos_max = (bb['y'] + bb['height']) * page_height

    ids_in_region: list[str] = []
    for elem in root.iter(f'{{{ALTO21_NS}}}String'):
        sid = elem.get('ID')
        if not sid:
            continue
        try:
            hpos = float(elem.get('HPOS', 0))
            vpos = float(elem.get('VPOS', 0))
            width = float(elem.get('WIDTH', 0))
            height = float(elem.get('HEIGHT', 0))
        except (TypeError, ValueError):
            continue
        if (hpos < hpos_max and (hpos + width) > hpos_min
                and vpos < vpos_max and (vpos + height) > vpos_min):
            ids_in_region.append(sid)

    if not ids_in_region:
        return None, None
    return ids_in_region[0], ids_in_region[-1]


# ---------------------------------------------------------------------------
# METS builder
# ---------------------------------------------------------------------------

def build_mets(output_dir: Path, issue_title: str = '') -> bytes:
    """Build a METS 1.12 document from ALTO XML and segment JSON files in output_dir.

    Discovers all ALTO files in output_dir/alto/, reads segment metadata from
    output_dir/segments/<stem>.json, and produces a conforming METS document.

    Args:
        output_dir: Root output directory (contains alto/, segments/ subdirectories).
        issue_title: Human-readable issue title for MODS descriptive metadata.

    Returns:
        UTF-8 encoded METS XML bytes.
    """
    alto_dir = output_dir / 'alto'
    seg_dir = output_dir / 'segments'

    alto_paths = sorted(alto_dir.glob('*.xml')) if alto_dir.exists() else []

    # Build page list
    pages: list[dict] = []
    for alto_path in alto_paths:
        stem = alto_path.stem
        seg_path = seg_dir / (stem + '.json')
        seg_data = None
        if seg_path.exists():
            try:
                seg_data = json.loads(seg_path.read_text())
            except Exception:
                pass
        pages.append({'stem': stem, 'alto_path': alto_path, 'seg_data': seg_data})

    # Root element
    root = etree.Element(_mets('mets'), nsmap=_NSMAP)
    root.set(
        f'{{{XSI_NS}}}schemaLocation',
        'http://www.loc.gov/METS/ http://www.loc.gov/standards/mets/mets.xsd',
    )

    # metsHdr
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    hdr = etree.SubElement(root, _mets('metsHdr'), CREATEDATE=now)
    agent = etree.SubElement(hdr, _mets('agent'), ROLE='CREATOR', TYPE='OTHER')
    etree.SubElement(agent, _mets('name')).text = 'Zeitschriften-OCR'

    # dmdSec (MODS)
    dmd = etree.SubElement(root, _mets('dmdSec'), ID='dmd_0')
    mdwrap = etree.SubElement(dmd, _mets('mdWrap'), MDTYPE='MODS')
    xmldata = etree.SubElement(mdwrap, _mets('xmlData'))
    mods_root = etree.SubElement(xmldata, _mods('mods'))
    ti = etree.SubElement(mods_root, _mods('titleInfo'))
    etree.SubElement(ti, _mods('title')).text = issue_title or 'Unknown Issue'
    etree.SubElement(mods_root, _mods('typeOfResource')).text = 'text'

    # fileSec — three file groups per DFG Viewer newspaper profile:
    #   MASTER   = original TIFF images
    #   DEFAULT  = scaled JPEG derivatives (viewer images)
    #   FULLTEXT = ALTO 2.1 XML (full-text / word coordinates)
    filesec = etree.SubElement(root, _mets('fileSec'))

    # MASTER — TIFFs
    grp_master = etree.SubElement(filesec, _mets('fileGrp'), USE='MASTER')
    # DEFAULT — JPEGs
    grp_default = etree.SubElement(filesec, _mets('fileGrp'), USE='DEFAULT')
    # FULLTEXT — ALTO XML
    grp_fulltext = etree.SubElement(filesec, _mets('fileGrp'), USE='FULLTEXT')

    tiff_ids: dict[str, str] = {}
    jpeg_ids: dict[str, str] = {}
    alto_ids: dict[str, str] = {}

    for i, page in enumerate(pages):
        stem = page['stem']

        tid = f'FILE_tiff_{i:04d}'
        tiff_ids[stem] = tid
        f_tiff = etree.SubElement(grp_master, _mets('file'), ID=tid, MIMETYPE='image/tiff')
        etree.SubElement(
            f_tiff, _mets('FLocat'), LOCTYPE='URL',
            **{f'{{{XLINK_NS}}}href': f'uploads/{stem}.tif'},
        )

        jid = f'FILE_jpeg_{i:04d}'
        jpeg_ids[stem] = jid
        f_jpeg = etree.SubElement(grp_default, _mets('file'), ID=jid, MIMETYPE='image/jpeg')
        etree.SubElement(
            f_jpeg, _mets('FLocat'), LOCTYPE='URL',
            **{f'{{{XLINK_NS}}}href': f'jpegcache/{stem}.jpg'},
        )

        aid = f'FILE_alto_{i:04d}'
        alto_ids[stem] = aid
        f_alto = etree.SubElement(grp_fulltext, _mets('file'), ID=aid, MIMETYPE='text/xml')
        etree.SubElement(
            f_alto, _mets('FLocat'), LOCTYPE='URL',
            **{f'{{{XLINK_NS}}}href': f'alto/{stem}.xml'},
        )

    # LOGICAL structMap
    log_map = etree.SubElement(root, _mets('structMap'), TYPE='LOGICAL')
    log_root_div = etree.SubElement(
        log_map, _mets('div'),
        TYPE='Newspaper',
        LABEL=issue_title or 'Unknown Issue',
        DMDID='dmd_0',
    )

    for page in pages:
        seg = page['seg_data']
        if not seg or not seg.get('regions'):
            continue

        try:
            alto_root = etree.parse(str(page['alto_path'])).getroot()
            alto_page = alto_root.find(f'.//{{{ALTO21_NS}}}Page')
            if alto_page is None:
                continue
            page_width = int(alto_page.get('WIDTH', 0))
            page_height = int(alto_page.get('HEIGHT', 0))
        except Exception:
            continue

        fid = alto_ids[page['stem']]
        for region in seg['regions']:
            div_type = region.get('type', 'article')
            div_label = region.get('title', '')
            div = etree.SubElement(log_root_div, _mets('div'), TYPE=div_type, LABEL=div_label)

            bb = region.get('bounding_box', {})
            if page_width and page_height and bb:
                begin_id, end_id = _find_word_ids_in_region(
                    alto_root, page_width, page_height, bb
                )
                if begin_id and end_id:
                    fptr = etree.SubElement(div, _mets('fptr'))
                    etree.SubElement(
                        fptr, _mets('area'),
                        FILEID=fid,
                        BEGIN=begin_id,
                        END=end_id,
                        BETYPE='IDREF',
                    )

    # PHYSICAL structMap
    phys_map = etree.SubElement(root, _mets('structMap'), TYPE='PHYSICAL')
    phys_root_div = etree.SubElement(phys_map, _mets('div'), TYPE='physSequence')

    for i, page in enumerate(pages):
        phys_div = etree.SubElement(
            phys_root_div, _mets('div'),
            ID=f'phys_{i:04d}',
            TYPE='page',
            ORDER=str(i + 1),
            ORDERLABEL=str(i + 1),
        )
        etree.SubElement(phys_div, _mets('fptr'), FILEID=tiff_ids[page['stem']])
        etree.SubElement(phys_div, _mets('fptr'), FILEID=jpeg_ids[page['stem']])
        etree.SubElement(phys_div, _mets('fptr'), FILEID=alto_ids[page['stem']])

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
