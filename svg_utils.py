# svg_utils.py
# Small helpers used by the checks: clean the model's raw text and read numbers.

import html.entities   # table of HTML entity names -> character codes
import re

# The only entities XML itself understands. Everything else (&sup2; &nbsp; &times; ...)
# is HTML-only and makes the XML parser fail.
XML_ENTITIES = ("amp", "lt", "gt", "quot", "apos")


def fix_entities(text):
    """Replace HTML-only entities like &sup2; with the real character (²)."""
    def replace(match):
        name = match.group(1)
        if name in XML_ENTITIES:                       # keep valid XML entities untouched
            return match.group(0)
        codepoint = html.entities.name2codepoint.get(name)
        if codepoint is None:                          # unknown name: leave it, the check will report it
            return match.group(0)
        return chr(codepoint)
    return re.sub(r"&([A-Za-z][A-Za-z0-9]*);", replace, text)


def extract_svg(raw_text):
    """Return only the <svg ...>...</svg> part of the model's reply, or None.

    Models often wrap SVG in ```svg fences or add chatter before/after it,
    so we cut everything outside the first <svg and the last </svg>.
    Then we convert HTML-only entities so the XML parser accepts the text.
    """
    start = raw_text.find("<svg")
    end = raw_text.rfind("</svg>")
    if start == -1 or end == -1 or end < start:    # no complete svg found
        return None
    return fix_entities(raw_text[start:end + len("</svg>")])


def to_float(value, default=None):
    """Turn strings like '120', '120.5', '120px' into a float.

    Returns `default` for things we can't read (like '50%').
    """
    if value is None:
        return default
    match = re.match(r"^\s*(-?\d+(\.\d+)?)\s*(px)?\s*$", str(value))   # number with optional px
    if not match:
        return default
    return float(match.group(1))


def parse_viewbox(viewbox_text):
    """Turn 'minx miny width height' into (min_x, min_y, width, height) floats.

    Returns None if the viewBox is missing or malformed.
    """
    if not viewbox_text:
        return None
    parts = re.split(r"[,\s]+", viewbox_text.strip())   # numbers may be separated by spaces or commas
    if len(parts) != 4:
        return None
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        return None
    return tuple(numbers)