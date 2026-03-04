"""vlm.py — VLM provider abstraction for newspaper article segmentation.

Supports Claude (Anthropic) and OpenAI providers.
Both SDKs are lazy-imported inside segment() so the module loads without them installed.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_PROVIDERS = ('claude', 'openai', 'openai_compatible')

SEGMENT_PROMPT = (
    'This is a page from a historical German periodical (journal or magazine).\n'
    'Identify ALL distinct content regions on this page. Be exhaustive — every visible text block, '
    'heading, advertisement, illustration, and caption must be accounted for.\n\n'
    'Layout notes:\n'
    '- Pages typically use multi-column layouts (2–4 columns)\n'
    '- A single article may span multiple columns; use ONE bounding box per article\n'
    '- Each article with its own headline is a SEPARATE region — never merge two articles into one box\n'
    '- Bounding boxes must be tight to the content edges (no large blank margins inside)\n'
    '- Together, all bounding boxes should cover the entire page area\n'
    '- Columns dividers, page numbers, and running headers are not separate regions\n\n'
    'For each region output:\n'
    '  - type: one of "headline", "article", "advertisement", "illustration", "caption"\n'
    '  - title: the article headline if legible, otherwise a brief German-language description\n'
    '  - bounding_box: {x, y, width, height} as floats 0.0\u20131.0 '
    '(fraction of image dimensions, origin top-left)\n\n'
    'Respond ONLY with valid JSON:\n'
    '{"regions": [{"type": "...", "title": "...", "bounding_box": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.2}}, ...]}\n\n'
    'If no regions are detectable, respond with: {"regions": []}'
)

VALID_TYPES = frozenset({'headline', 'article', 'advertisement', 'illustration', 'caption'})


# ---------------------------------------------------------------------------
# Provider base class
# ---------------------------------------------------------------------------

class SegmentationProvider:
    """Abstract base for VLM segmentation providers."""

    def segment(self, jpeg_path: Path) -> list[dict]:
        """Send jpeg_path to the VLM and return parsed region list.

        Returns a list of region dicts with keys: id, type, title, bounding_box.
        Raises on API errors (caller handles and returns 502).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Claude provider
# ---------------------------------------------------------------------------

class ClaudeProvider(SegmentationProvider):

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.api_key = api_key

    def segment(self, jpeg_path: Path) -> list[dict]:
        import anthropic  # lazy — only required if claude provider is used
        data = jpeg_path.read_bytes()
        b64 = base64.b64encode(data).decode()
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64},
                    },
                    {'type': 'text', 'text': SEGMENT_PROMPT},
                ],
            }],
        )
        text = response.content[0].text
        return _parse_regions(text)


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(SegmentationProvider):

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.api_key = api_key

    def segment(self, jpeg_path: Path) -> list[dict]:
        import openai  # lazy — only required if openai provider is used
        data = jpeg_path.read_bytes()
        b64 = base64.b64encode(data).decode()
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:image/jpeg;base64,{b64}'},
                    },
                    {'type': 'text', 'text': SEGMENT_PROMPT},
                ],
            }],
            max_tokens=4096,
        )
        text = response.choices[0].message.content
        return _parse_regions(text)


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (Open WebUI, OpenRouter, Ollama, etc.)
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider(SegmentationProvider):
    """Provider for any OpenAI-compatible API (Open WebUI, OpenRouter, Ollama).

    Uses openai.OpenAI with a custom base_url — works with any backend
    that implements the /v1/chat/completions endpoint.
    """

    def __init__(self, model: str, api_key: str, base_url: str) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def segment(self, jpeg_path: Path) -> list[dict]:
        import openai  # lazy — only required at call time
        data = jpeg_path.read_bytes()
        b64 = base64.b64encode(data).decode()
        client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:image/jpeg;base64,{b64}'},
                    },
                    {'type': 'text', 'text': SEGMENT_PROMPT},
                ],
            }],
            max_tokens=4096,
        )
        text = response.choices[0].message.content
        return _parse_regions(text)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_provider(name: str, model: str, api_key: str, *, base_url: str = '') -> SegmentationProvider:
    """Return a configured SegmentationProvider for the given provider name.

    Args:
        name: Provider name — 'claude', 'openai', or 'openai_compatible'.
        model: Model identifier.
        api_key: API key string.
        base_url: Base URL for OpenAI-compatible providers (required for 'openai_compatible').

    Raises:
        ValueError: If name is not a supported provider.
    """
    if name == 'claude':
        return ClaudeProvider(model, api_key)
    if name == 'openai':
        return OpenAIProvider(model, api_key)
    if name == 'openai_compatible':
        return OpenAICompatibleProvider(model, api_key, base_url)
    raise ValueError(
        f'Unknown VLM provider: {name!r}. Supported: {", ".join(SUPPORTED_PROVIDERS)}'
    )


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_regions(text: str) -> list[dict]:
    """Extract and validate region list from a VLM response string.

    Handles VLM preamble/postamble by searching for the first JSON object.
    Strips markdown code fences (```json ... ```) before parsing.
    Filters regions with invalid type. Assigns sequential 'r{N}' IDs.
    Returns [] on any parse or validation failure — never raises.
    """
    # Strip markdown code fences that some models wrap around JSON
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    raw_regions = parsed.get('regions', [])
    if not isinstance(raw_regions, list):
        return []
    result = []
    for raw in raw_regions:
        if not isinstance(raw, dict):
            continue
        rtype = raw.get('type', '')
        if rtype not in VALID_TYPES:
            continue
        bb = raw.get('bounding_box')
        if not isinstance(bb, dict):
            continue
        try:
            region = {
                'id': f'r{len(result)}',
                'type': rtype,
                'title': str(raw.get('title', '')),
                'bounding_box': {
                    'x': float(bb.get('x', 0)),
                    'y': float(bb.get('y', 0)),
                    'width': float(bb.get('width', 1)),
                    'height': float(bb.get('height', 1)),
                },
            }
            result.append(region)
        except (TypeError, ValueError):
            continue
    return result
