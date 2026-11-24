"""Render a padded static SVG snapshot to detect visible overflow.

The renderer does not execute SMIL/CSS animation; callers must separately flag
animated geometry for review.  A padded raster is a practical check, not proof
about unlimited off-screen coordinates or browser-specific font rendering.
"""
import copy
import io
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from functools import lru_cache

from svg_utils import parse_viewbox

MAX_SVG_BYTES = 1_000_000
MAX_RENDER_SIDE = 1800
FONT_PATH = Path(__file__).resolve().parent / "static" / "fonts" / "DejaVuSans.ttf"


@lru_cache(maxsize=32)
def rendered_bounds(svg_text):
    if len(svg_text.encode('utf-8')) > MAX_SVG_BYTES:
        return None, 'SVG is too large for the bounded renderer.'
    try:
        from PIL import Image
        from resvg_py import svg_to_bytes
        root = ET.fromstring(svg_text)
        viewbox = parse_viewbox(root.get('viewBox'))
        if not viewbox:
            return False, 'Invalid viewBox.'
        # Never allow the renderer to resolve external resources from generated content.
        for element in root.iter():
            for name, value in element.attrib.items():
                if name.split('}')[-1].lower() in ('href', 'src') and not value.strip().startswith('#'):
                    return None, 'External resources cannot be rendered safely.'
                for ref in re.findall(r'url\(\s*[\'"]?([^\)\'"]+)', value, re.I):
                    if not ref.strip().startswith('#'):
                        return None, 'External CSS resources cannot be rendered safely.'
            if element.tag.split('}')[-1] == 'style':
                css = ''.join(element.itertext())
                if '@import' in css.lower():
                    return None, 'Imported styles cannot be rendered safely.'
                for ref in re.findall(r'url\(\s*[\'"]?([^\)\'"]+)', css, re.I):
                    if not ref.strip().startswith('#'):
                        return None, 'External CSS resources cannot be rendered safely.'
        root = copy.deepcopy(root)
        # SMIL motion is not executed by resvg; omit moving elements instead of
        # reporting their unanimated origin as an actual overflow.
        def remove_motion(parent):
            for child in list(parent):
                if any(c.tag.split('}')[-1] == 'animateMotion' for c in child):
                    parent.remove(child)
                else:
                    remove_motion(child)
        remove_motion(root)
        x, y, width, height = viewbox
        root.set('viewBox', f'{x-width} {y-height} {width*3} {height*3}')
        scale = MAX_RENDER_SIDE / max(width * 3, height * 3)
        px_width = max(3, round(width * 3 * scale))
        px_height = max(3, round(height * 3 * scale))
        root.set('width', str(px_width))
        root.set('height', str(px_height))
        if not FONT_PATH.is_file():
            return None, 'Renderer font is unavailable; review text bounds manually.'
        png = svg_to_bytes(svg_string=ET.tostring(root, encoding='unicode'), width=px_width, height=px_height,
                           skip_system_fonts=True, font_files=[str(FONT_PATH)], font_family='DejaVu Sans',
                           serif_family='DejaVu Sans', sans_serif_family='DejaVu Sans',
                           monospace_family='DejaVu Sans')
        image = Image.open(io.BytesIO(png)).convert('RGBA')
        alpha = image.getchannel('A')
        # Permit two pixels at the edge for antialiasing.
        left, top = px_width // 3, px_height // 3
        right, bottom = px_width - left, px_height - top
        strips = [(0, 0, max(0, left-2), px_height), (min(px_width, right+2), 0, px_width, px_height),
                  (0, 0, px_width, max(0, top-2)), (0, min(px_height, bottom+2), px_width, px_height)]
        for box in strips:
            if box[2] > box[0] and box[3] > box[1] and alpha.crop(box).getbbox():
                return False, 'Rendered static content extends outside the viewBox.'
        return True, 'Padded static rendering found no visible overflow using a bundled fallback font; browser fonts and animation may differ.'
    except Exception:
        # Renderer errors should never be mistaken for a pass or crash a generation.
        return None, 'Static rendering could not be completed; review the bounds manually.'
