"""Tests for mets.py builder and GET /mets endpoint — Phase 16 (STRUCT-04)."""
import json
from pathlib import Path

import pytest
from lxml import etree

import mets as mets_module

METS_NS = mets_module.METS_NS
MODS_NS = mets_module.MODS_NS

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ALTO_FIXTURE = b"""<?xml version='1.0' encoding='UTF-8'?>
<alto xmlns="http://schema.ccs-gmbh.com/ALTO">
  <Description><MeasurementUnit>pixel</MeasurementUnit></Description>
  <Layout>
    <Page WIDTH="4000" HEIGHT="6000" PHYSICAL_IMG_NR="0" ID="page_0">
      <PrintSpace HPOS="0" VPOS="0" WIDTH="4000" HEIGHT="6000">
        <TextBlock ID="block_0" HPOS="0" VPOS="0" WIDTH="4000" HEIGHT="500">
          <TextLine ID="line_0" HPOS="0" VPOS="50" WIDTH="4000" HEIGHT="150">
            <String ID="string_0" HPOS="100" VPOS="50" WIDTH="300" HEIGHT="150" WC="0.95" CONTENT="Hello"/>
            <String ID="string_1" HPOS="450" VPOS="50" WIDTH="300" HEIGHT="150" WC="0.90" CONTENT="World"/>
            <String ID="string_2" HPOS="800" VPOS="50" WIDTH="300" HEIGHT="150" WC="0.88" CONTENT="Test"/>
          </TextLine>
        </TextBlock>
      </PrintSpace>
    </Page>
  </Layout>
</alto>"""

SEG_FIXTURE = {
    'stem': 'page001',
    'provider': 'claude',
    'model': 'claude-opus-4-6',
    'segmented_at': '2026-03-01T00:00:00',
    'regions': [
        {
            'id': 'r0',
            'type': 'article',
            'title': 'Test Article',
            'bounding_box': {'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 0.2},
        }
    ],
}


def _setup_output(tmp_path, with_segments=True, regions=None):
    """Create alto/ and optionally segments/ test fixtures."""
    alto_dir = tmp_path / 'alto'
    alto_dir.mkdir()
    (alto_dir / 'page001.xml').write_bytes(ALTO_FIXTURE)
    if with_segments:
        seg_dir = tmp_path / 'segments'
        seg_dir.mkdir()
        seg = dict(SEG_FIXTURE)
        if regions is not None:
            seg = {**seg, 'regions': regions}
        (seg_dir / 'page001.json').write_text(json.dumps(seg))
    return tmp_path


# ---------------------------------------------------------------------------
# _find_word_ids_in_region
# ---------------------------------------------------------------------------

class TestFindWordIdsInRegion:

    def _root(self):
        return etree.fromstring(ALTO_FIXTURE)

    def test_full_page_region_returns_first_and_last(self):
        root = self._root()
        begin, end = mets_module._find_word_ids_in_region(
            root, 4000, 6000, {'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 1.0}
        )
        assert begin == 'string_0'
        assert end == 'string_2'

    def test_no_strings_in_region_returns_none_none(self):
        root = self._root()
        # Region in bottom half — no strings there
        begin, end = mets_module._find_word_ids_in_region(
            root, 4000, 6000, {'x': 0.0, 'y': 0.8, 'width': 1.0, 'height': 0.2}
        )
        assert begin is None
        assert end is None

    def test_top_strip_returns_first_string(self):
        root = self._root()
        # Region covering top 5% — strings at VPOS=50 (0.83% of 6000) should be in it
        begin, end = mets_module._find_word_ids_in_region(
            root, 4000, 6000, {'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 0.05}
        )
        assert begin == 'string_0'
        assert end == 'string_2'

    def test_left_column_returns_first_string_only(self):
        root = self._root()
        # Left column: x=0..0.1 (0..400px) — only string_0 at HPOS=100, WIDTH=300 → right edge=400
        begin, end = mets_module._find_word_ids_in_region(
            root, 4000, 6000, {'x': 0.0, 'y': 0.0, 'width': 0.1, 'height': 0.1}
        )
        assert begin == 'string_0'
        assert end == 'string_0'


# ---------------------------------------------------------------------------
# build_mets
# ---------------------------------------------------------------------------

class TestBuildMets:

    def test_returns_bytes_starting_with_xml_declaration(self, tmp_path):
        _setup_output(tmp_path)
        result = mets_module.build_mets(tmp_path)
        assert isinstance(result, bytes)
        assert result.startswith(b'<?xml')

    def test_root_element_is_mets(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        assert root.tag == f'{{{METS_NS}}}mets'

    def test_dmdsec_with_issue_title(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path, issue_title='Test Zeitung'))
        title = root.find(f'.//{{{MODS_NS}}}title')
        assert title is not None
        assert title.text == 'Test Zeitung'

    def test_dmdsec_default_title_when_empty(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        title = root.find(f'.//{{{MODS_NS}}}title')
        assert title is not None
        assert title.text  # non-empty fallback

    def test_filesec_contains_one_file_per_alto(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        files = root.findall(f'.//{{{METS_NS}}}file')
        # 3 file groups (MASTER/DEFAULT/FULLTEXT) × 1 page = 3 files
        assert len(files) == 3
        ids = {f.get('ID') for f in files}
        assert 'FILE_tiff_0000' in ids
        assert 'FILE_jpeg_0000' in ids
        assert 'FILE_alto_0000' in ids
        mimetypes = {f.get('ID'): f.get('MIMETYPE') for f in files}
        assert mimetypes['FILE_tiff_0000'] == 'image/tiff'
        assert mimetypes['FILE_jpeg_0000'] == 'image/jpeg'
        assert mimetypes['FILE_alto_0000'] == 'text/xml'

    def test_both_structmaps_present(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        structmaps = root.findall(f'{{{METS_NS}}}structMap')
        types = {sm.get('TYPE') for sm in structmaps}
        assert 'LOGICAL' in types
        assert 'PHYSICAL' in types

    def test_article_div_in_logical_structmap(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        divs = root.findall(f'.//{{{METS_NS}}}div[@TYPE="article"]')
        assert len(divs) == 1
        assert divs[0].get('LABEL') == 'Test Article'

    def test_area_element_links_to_word_ids(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        area = root.find(f'.//{{{METS_NS}}}area')
        assert area is not None
        assert area.get('FILEID') == 'FILE_alto_0000'
        assert area.get('BETYPE') == 'IDREF'
        assert area.get('BEGIN') == 'string_0'
        assert area.get('END') == 'string_2'

    def test_physical_structmap_has_page_div(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        page_divs = root.findall(f'.//{{{METS_NS}}}div[@TYPE="page"]')
        assert len(page_divs) == 1
        assert page_divs[0].get('ORDER') == '1'

    def test_no_alto_files_returns_valid_mets(self, tmp_path):
        result = mets_module.build_mets(tmp_path)
        root = etree.fromstring(result)
        assert root.tag == f'{{{METS_NS}}}mets'

    def test_alto_without_segments_has_no_article_divs(self, tmp_path):
        _setup_output(tmp_path, with_segments=False)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        divs = root.findall(f'.//{{{METS_NS}}}div[@TYPE="article"]')
        assert len(divs) == 0

    def test_empty_regions_list_has_no_article_divs(self, tmp_path):
        _setup_output(tmp_path, regions=[])
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        divs = root.findall(f'.//{{{METS_NS}}}div[@TYPE="article"]')
        assert len(divs) == 0

    def test_multiple_alto_files_sorted_order(self, tmp_path):
        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        (alto_dir / 'page002.xml').write_bytes(ALTO_FIXTURE)
        (alto_dir / 'page001.xml').write_bytes(ALTO_FIXTURE)
        root = etree.fromstring(mets_module.build_mets(tmp_path))
        files = root.findall(f'.//{{{METS_NS}}}file')
        # 3 file groups × 2 pages = 6 files
        assert len(files) == 6
        # First file (FILE_tiff_0000) should be page001 in sorted order
        flocat = files[0].find(f'{{{METS_NS}}}FLocat')
        href = list(flocat.attrib.values())
        assert any('page001' in v for v in href)

    def test_rerun_same_element_count(self, tmp_path):
        _setup_output(tmp_path)
        r1 = etree.fromstring(mets_module.build_mets(tmp_path, issue_title='T'))
        r2 = etree.fromstring(mets_module.build_mets(tmp_path, issue_title='T'))
        assert len(list(r1.iter())) == len(list(r2.iter()))


# ---------------------------------------------------------------------------
# GET /mets endpoint
# ---------------------------------------------------------------------------

class TestGetMetsEndpoint:

    def test_returns_xml_download_when_alto_exists(self, client, flask_app, tmp_path):
        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        (alto_dir / 'page001.xml').write_bytes(ALTO_FIXTURE)
        resp = client.get('/mets')
        assert resp.status_code == 200
        assert resp.mimetype == 'application/xml'
        assert 'mets.xml' in resp.headers.get('Content-Disposition', '')

    def test_returns_204_when_no_alto_files(self, client, flask_app, tmp_path):
        resp = client.get('/mets')
        assert resp.status_code == 204

    def test_issue_title_from_config(self, client, flask_app, tmp_path):
        flask_app.config['ISSUE_TITLE'] = 'Meine Zeitung'
        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        (alto_dir / 'page001.xml').write_bytes(ALTO_FIXTURE)
        resp = client.get('/mets')
        assert resp.status_code == 200
        assert b'Meine Zeitung' in resp.data

    def test_response_is_valid_xml(self, client, flask_app, tmp_path):
        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir()
        (alto_dir / 'page001.xml').write_bytes(ALTO_FIXTURE)
        resp = client.get('/mets')
        assert resp.status_code == 200
        root = etree.fromstring(resp.data)
        assert root.tag == f'{{{METS_NS}}}mets'
