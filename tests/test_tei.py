"""Tests for tei.py builder — Phase 21 (TEI-01, TEI-02, TEI-03)."""
import json
from pathlib import Path

import pytest
from lxml import etree

import tei as tei_module

TEI_NS = tei_module.TEI_NS
XML_NS = 'http://www.w3.org/XML/1998/namespace'

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Two TextBlocks on a 4000×6000 page.
# Block 0: HPOS=0, VPOS=0, WIDTH=1800, HEIGHT=3000 (left column)
#   TextLine 0: HPOS=0, VPOS=50, HEIGHT=150  — "Hello" and "World" (World is line_end)
#   TextLine 1: HPOS=0, VPOS=250, HEIGHT=150 — "Ver-" only (Ver- is line_end → triggers rejoin)
#   TextLine 2: HPOS=0, VPOS=450, HEIGHT=150 — "Test" only (continuation of Ver-)
# Block 1: HPOS=2200, VPOS=0, WIDTH=1800, HEIGHT=3000 (right column)
#   TextLine 0: HPOS=2200, VPOS=50, HEIGHT=150  — "Right" and "Column" (Column is line_end)
#   TextLine 1: HPOS=2200, VPOS=250, HEIGHT=150 — "End" only (End is line_end)

ALTO_FIXTURE = b"""<?xml version='1.0' encoding='UTF-8'?>
<alto xmlns="http://schema.ccs-gmbh.com/ALTO">
  <Description><MeasurementUnit>pixel</MeasurementUnit></Description>
  <Layout>
    <Page WIDTH="4000" HEIGHT="6000" PHYSICAL_IMG_NR="0" ID="page_0">
      <PrintSpace HPOS="0" VPOS="0" WIDTH="4000" HEIGHT="6000">
        <TextBlock ID="block_0" HPOS="0" VPOS="0" WIDTH="1800" HEIGHT="3000">
          <TextLine ID="line_0" HPOS="0" VPOS="50" WIDTH="1800" HEIGHT="150">
            <String ID="string_0" HPOS="100" VPOS="50" WIDTH="200" HEIGHT="150" WC="0.95" CONTENT="Hello"/>
            <String ID="string_1" HPOS="450" VPOS="50" WIDTH="200" HEIGHT="150" WC="0.95" CONTENT="World"/>
          </TextLine>
          <TextLine ID="line_1" HPOS="0" VPOS="250" WIDTH="1800" HEIGHT="150">
            <String ID="string_2" HPOS="100" VPOS="250" WIDTH="200" HEIGHT="150" WC="0.90" CONTENT="Ver-"/>
          </TextLine>
          <TextLine ID="line_2" HPOS="0" VPOS="450" WIDTH="1800" HEIGHT="150">
            <String ID="string_3" HPOS="100" VPOS="450" WIDTH="200" HEIGHT="150" WC="0.90" CONTENT="Test"/>
          </TextLine>
        </TextBlock>
        <TextBlock ID="block_1" HPOS="2200" VPOS="0" WIDTH="1800" HEIGHT="3000">
          <TextLine ID="line_3" HPOS="2200" VPOS="50" WIDTH="1800" HEIGHT="150">
            <String ID="string_4" HPOS="2200" VPOS="50" WIDTH="200" HEIGHT="150" WC="0.92" CONTENT="Right"/>
            <String ID="string_5" HPOS="2600" VPOS="50" WIDTH="200" HEIGHT="150" WC="0.92" CONTENT="Column"/>
          </TextLine>
          <TextLine ID="line_4" HPOS="2200" VPOS="250" WIDTH="1800" HEIGHT="150">
            <String ID="string_6" HPOS="2200" VPOS="250" WIDTH="200" HEIGHT="150" WC="0.88" CONTENT="End"/>
          </TextLine>
        </TextBlock>
      </PrintSpace>
    </Page>
  </Layout>
</alto>"""

# SEG_FIXTURE: one region covering the left half of the page (x=0..0.5)
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
            'bounding_box': {'x': 0.0, 'y': 0.0, 'width': 0.5, 'height': 1.0},
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
# TestBuildTeiNamespace
# ---------------------------------------------------------------------------

class TestBuildTeiNamespace:

    def test_returns_bytes_with_xml_declaration(self, tmp_path):
        _setup_output(tmp_path)
        result = tei_module.build_tei(tmp_path, 'page001')
        assert isinstance(result, bytes)
        assert result.startswith(b'<?xml')

    def test_root_is_tei_element_with_tei_namespace(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        assert root.tag == f'{{{TEI_NS}}}TEI'

    def test_facsimile_surface_has_correct_xml_id(self, tmp_path):
        """xml:id on <surface> must NOT have hash prefix."""
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        surfaces = root.findall(f'.//{{{TEI_NS}}}surface')
        assert len(surfaces) == 1
        xml_id = surfaces[0].get(f'{{{XML_NS}}}id')
        assert xml_id == 'page-page001'
        assert not xml_id.startswith('#')

    def test_pb_facs_has_hash_prefix(self, tmp_path):
        """facs on <pb> must use #fragment-identifier syntax."""
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        pbs = root.findall(f'.//{{{TEI_NS}}}pb')
        assert len(pbs) >= 1
        facs = pbs[0].get('facs')
        assert facs == '#page-page001'


# ---------------------------------------------------------------------------
# TestBuildTeiFacsimile
# ---------------------------------------------------------------------------

class TestBuildTeiFacsimile:

    def test_surface_uses_alto_page_dimensions_not_jpeg(self, tmp_path):
        """ulx/uly/lrx/lry on <surface> must come from ALTO <Page WIDTH HEIGHT>."""
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        surface = root.find(f'.//{{{TEI_NS}}}surface')
        assert surface is not None
        assert surface.get('ulx') == '0'
        assert surface.get('uly') == '0'
        assert surface.get('lrx') == '4000'
        assert surface.get('lry') == '6000'

    def test_zone_coordinates_in_alto_pixel_space(self, tmp_path):
        """Zone ulx/uly/lrx/lry must be ALTO pixel coords (fractional * page dims)."""
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        zones = root.findall(f'.//{{{TEI_NS}}}zone')
        assert len(zones) == 1
        zone = zones[0]
        # Region: x=0.0, y=0.0, width=0.5, height=1.0 on 4000×6000 page
        assert zone.get('ulx') == '0'
        assert zone.get('uly') == '0'
        assert zone.get('lrx') == '2000'   # 0.5 * 4000
        assert zone.get('lry') == '6000'   # 1.0 * 6000

    def test_no_segments_has_no_zone_elements(self, tmp_path):
        """Without VLM segments, <facsimile> has surface but no zone elements."""
        _setup_output(tmp_path, with_segments=False)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        zones = root.findall(f'.//{{{TEI_NS}}}zone')
        assert len(zones) == 0
        # surface must still be present
        surfaces = root.findall(f'.//{{{TEI_NS}}}surface')
        assert len(surfaces) == 1


# ---------------------------------------------------------------------------
# TestBuildTeiBody
# ---------------------------------------------------------------------------

class TestBuildTeiBody:

    def test_single_region_produces_one_article_div(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        divs = root.findall(f'.//{{{TEI_NS}}}div[@type="article"]')
        assert len(divs) == 1

    def test_no_segments_produces_single_fallback_div_with_comment(self, tmp_path):
        """No VLM data: one <div type='article'> and XML comment in body."""
        _setup_output(tmp_path, with_segments=False)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        divs = root.findall(f'.//{{{TEI_NS}}}div[@type="article"]')
        assert len(divs) == 1
        # Body should contain an XML comment about absent VLM data
        body = root.find(f'.//{{{TEI_NS}}}body')
        assert body is not None
        comments = [c for c in body if isinstance(c, etree._Comment)]
        assert len(comments) == 1
        assert 'VLM' in comments[0].text

    def test_article_div_has_n_attribute(self, tmp_path):
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        divs = root.findall(f'.//{{{TEI_NS}}}div[@type="article"]')
        assert len(divs) == 1
        assert divs[0].get('n') == '1'

    def test_region_title_becomes_head_element(self, tmp_path):
        """VLM region with title='Test Article' should produce <head>Test Article</head>."""
        _setup_output(tmp_path)
        root = etree.fromstring(tei_module.build_tei(tmp_path, 'page001'))
        heads = root.findall(f'.//{{{TEI_NS}}}head')
        assert len(heads) >= 1
        assert heads[0].text == 'Test Article'


# ---------------------------------------------------------------------------
# TestBuildTeiLineBreaks
# ---------------------------------------------------------------------------

class TestBuildTeiLineBreaks:

    def test_lb_between_lines_not_after_last_line(self, tmp_path):
        """<lb/> must appear between lines but NOT as a trailing empty element at end of <p>.

        In lxml mixed content, <lb/> between two lines has the next line's text in its .tail.
        A trailing <lb/> would have an empty or None tail — that is forbidden.
        """
        _setup_output(tmp_path, with_segments=False)
        result = tei_module.build_tei(tmp_path, 'page001')
        root = etree.fromstring(result)
        ps = root.findall(f'.//{{{TEI_NS}}}p')
        assert len(ps) >= 1
        for p in ps:
            children = list(p)
            if children:
                last_child = children[-1]
                if last_child.tag == f'{{{TEI_NS}}}lb':
                    # Last child is lb — only allowed if it has non-empty tail text
                    # (meaning more text follows on the next line, e.g. "Right Column<lb/>End")
                    tail = last_child.tail or ''
                    assert tail.strip(), (
                        f'<p> ends with trailing <lb/> that has empty tail — '
                        f'no text follows the last line boundary'
                    )

    def test_hyphen_rejoin_suppresses_intermediate_lb(self, tmp_path):
        """'Ver-' + 'Test' across a line boundary should NOT have an lb between them."""
        _setup_output(tmp_path, with_segments=False)
        result = tei_module.build_tei(tmp_path, 'page001')
        xml_str = result.decode('utf-8')
        # After rejoin, "Ver-" and "Test" are merged — so "Vertest" or "Ver-Test" joined
        # The intermediate lb between them must be suppressed
        # Check that "Ver-" does not appear in output (it was rejoined)
        assert 'Ver-' not in xml_str

    def test_rejoined_word_text_correct(self, tmp_path):
        """'Ver-' + 'Test' rejoins to 'VerTest' (hyphen removed from first fragment)."""
        _setup_output(tmp_path, with_segments=False)
        result = tei_module.build_tei(tmp_path, 'page001')
        xml_str = result.decode('utf-8')
        # The rejoined form should be "VerTest" (hyphen stripped, words concatenated)
        assert 'VerTest' in xml_str


# ---------------------------------------------------------------------------
# TestBuildTeiColumnSort
# ---------------------------------------------------------------------------

class TestBuildTeiColumnSort:

    def test_two_column_layout_left_before_right(self, tmp_path):
        """Left column words (Hello, World) appear before right column words (Right, Column)."""
        _setup_output(tmp_path, with_segments=False)
        result = tei_module.build_tei(tmp_path, 'page001')
        xml_str = result.decode('utf-8')
        # "Hello" must appear before "Right" in the serialized XML
        pos_hello = xml_str.find('Hello')
        pos_right = xml_str.find('Right')
        assert pos_hello != -1
        assert pos_right != -1
        assert pos_hello < pos_right, (
            f'Expected "Hello" (left column) before "Right" (right column), '
            f'but Hello at {pos_hello}, Right at {pos_right}'
        )

    def test_full_width_block_sorts_before_column_blocks(self, tmp_path):
        """A full-width block (WIDTH > 60% page_width) appears before narrow column blocks."""
        # Create an ALTO with one full-width block and one narrow block
        alto_with_header = b"""<?xml version='1.0' encoding='UTF-8'?>
<alto xmlns="http://schema.ccs-gmbh.com/ALTO">
  <Description><MeasurementUnit>pixel</MeasurementUnit></Description>
  <Layout>
    <Page WIDTH="4000" HEIGHT="6000" PHYSICAL_IMG_NR="0" ID="page_0">
      <PrintSpace HPOS="0" VPOS="0" WIDTH="4000" HEIGHT="6000">
        <TextBlock ID="block_narrow" HPOS="2200" VPOS="0" WIDTH="1800" HEIGHT="500">
          <TextLine ID="line_narrow" HPOS="2200" VPOS="50" WIDTH="1800" HEIGHT="150">
            <String ID="str_narrow" HPOS="2200" VPOS="50" WIDTH="200" HEIGHT="150" WC="0.90" CONTENT="NarrowBlock"/>
          </TextLine>
        </TextBlock>
        <TextBlock ID="block_full" HPOS="0" VPOS="1000" WIDTH="4000" HEIGHT="500">
          <TextLine ID="line_full" HPOS="0" VPOS="1050" WIDTH="4000" HEIGHT="150">
            <String ID="str_full" HPOS="100" VPOS="1050" WIDTH="200" HEIGHT="150" WC="0.95" CONTENT="FullWidth"/>
          </TextLine>
        </TextBlock>
      </PrintSpace>
    </Page>
  </Layout>
</alto>"""
        alto_dir = tmp_path / 'alto'
        alto_dir.mkdir(exist_ok=True)
        (alto_dir / 'fulltest.xml').write_bytes(alto_with_header)
        result = tei_module.build_tei(tmp_path, 'fulltest')
        xml_str = result.decode('utf-8')
        pos_full = xml_str.find('FullWidth')
        pos_narrow = xml_str.find('NarrowBlock')
        assert pos_full != -1
        assert pos_narrow != -1
        assert pos_full < pos_narrow, (
            f'Expected full-width block word before narrow column word, '
            f'but FullWidth at {pos_full}, NarrowBlock at {pos_narrow}'
        )


# ---------------------------------------------------------------------------
# TestBuildTeiIdempotent
# ---------------------------------------------------------------------------

class TestBuildTeiIdempotent:

    def test_repeated_calls_identical_bytes(self, tmp_path):
        """build_tei called twice with same inputs must return identical bytes."""
        _setup_output(tmp_path)
        result1 = tei_module.build_tei(tmp_path, 'page001')
        result2 = tei_module.build_tei(tmp_path, 'page001')
        assert result1 == result2
