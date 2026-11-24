# svg_utils.py
# Small helpers used by the checks: clean the model's raw text and read numbers.

import re


def extract_svg(raw_text):
    """Return only the <svg ...>...</svg> part of the model's reply, or None.

    Models often wrap SVG in ```svg fences or add chatter before/after it,
    so we cut everything outside the first <svg and the last </svg>.
    """
    start = raw_text.find("<svg")
    end = raw_text.rfind("</svg>")
    if start == -1 or end == -1 or end < start:    # no complete svg found
        return None
    return raw_text[start:end + len("</svg>")]


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