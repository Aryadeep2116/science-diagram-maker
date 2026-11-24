# checks.py
# Automatic checks on the SVG the model returns.
# Every check is a small function that returns (passed: bool, reason: str).
# The reason text is also fed back to the model if a retry is needed.

import re                                   # used in Steps 8 and 9 (path and number parsing)
import xml.etree.ElementTree as ET          # Python's built-in XML parser
import config                               # for MIN_TEXT_LABELS
from svg_utils import parse_viewbox, to_float   # used in Step 8


def local_name(tag):
    """Remove the namespace from a tag name.

    The parser gives '{http://www.w3.org/2000/svg}circle'; we only want 'circle'.
    """
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_svg(svg_text):
    """Parse SVG text into an element tree. Raises ET.ParseError if broken."""
    return ET.fromstring(svg_text)


# ---------- Check 1: is it valid, parseable SVG? ----------
def valid_xml(svg_text):
    """Pass if the text is well-formed XML whose root element is <svg>."""
    if not svg_text or not svg_text.strip():       # nothing to parse
        return False, "No complete <svg>...</svg> element was found in the reply."
    try:
        root = parse_svg(svg_text)
    except ET.ParseError as error:                 # the parser tells us what is wrong
        return False, f"The SVG is not well-formed XML: {error}"
    if local_name(root.tag) != "svg":              # e.g. a <html> page by mistake
        return False, "The root element is not <svg>."
    return True, "SVG parsed correctly."


# ---------- Check 2: has a title and at least 3 text labels ----------
def title_and_labels(svg_text):
    """Pass if there is a non-empty <title> directly inside <svg> and >= 3 non-empty <text> labels."""
    root = parse_svg(svg_text)

    title_text = ""
    for child in root:                             # only direct children of <svg>
        if local_name(child.tag) == "title":
            title_text = (child.text or "").strip()

    label_count = 0
    for element in root.iter():                    # root.iter() visits every element at any depth
        if local_name(element.tag) == "text":
            content = "".join(element.itertext()).strip()   # itertext() includes text inside <tspan>
            if content:                            # empty <text> does not count as a label
                label_count += 1

    problems = []
    if not title_text:
        problems.append("there is no non-empty <title> directly inside <svg>")
    if label_count < config.MIN_TEXT_LABELS:
        problems.append(f"there are only {label_count} <text> labels, at least {config.MIN_TEXT_LABELS} are needed")
    if problems:
        return False, "Problems: " + "; ".join(problems) + "."
    return True, f"Title found and {label_count} text labels."


# ---------- Check 3: has at least one animation ----------
ANIMATION_TAGS = ("animate", "animateTransform", "animateMotion", "set")   # SMIL animation elements


def has_animation(svg_text):
    """Pass if the SVG has a SMIL animation element, or CSS @keyframes plus an animation property."""
    root = parse_svg(svg_text)
    for element in root.iter():
        name = local_name(element.tag)
        if name in ANIMATION_TAGS:
            return True, f"Found a <{name}> animation."
        if name == "style":                        # CSS animation lives inside a <style> block
            css = element.text or ""
            if "@keyframes" in css and "animation" in css:
                return True, "Found a CSS @keyframes animation."
    return False, ("No animation found. Add SMIL elements (<animate>, <animateTransform>, "
                   "<animateMotion>) or a CSS @keyframes rule used by an animation property.")




# ---------- Check 4: nothing is drawn outside the viewBox ----------
# We only test STATIC positions. Elements with a transform="..." attribute are skipped
# (with their children), because evaluating transforms is complicated. Animated
# movement is also not simulated. Elements inside <defs> etc. are not drawn directly, so skipped.
SKIP_CONTAINERS = ("defs", "clipPath", "mask", "pattern", "marker", "symbol")


def _number(element, name, default=0.0):
    """Read a numeric attribute. Missing -> default. Unreadable (e.g. '50%') -> None."""
    raw = element.get(name)
    if raw is None:
        return default
    return to_float(raw)


def _points_from_list(text):
    """Turn '10,20 30,40' into [(10.0, 20.0), (30.0, 40.0)]."""
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    values = [float(n) for n in numbers]
    points = []
    for i in range(0, len(values) - 1, 2):         # take numbers two at a time
        points.append((values[i], values[i + 1]))
    return points


def _path_points(d):
    """Corner points of a simple path that only uses ABSOLUTE M, L, H, V, Z commands.

    Returns None if the path uses anything else (curves, relative commands),
    meaning 'cannot evaluate, skip it'.
    """
    for letter in re.findall(r"[A-Za-z]", d):
        if letter not in "MLHVZ":
            return None
    x, y = 0.0, 0.0
    points = []
    for command, args in re.findall(r"([MLHVZ])([^MLHVZ]*)", d):
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", args)]
        if command in "ML":                        # move / line: x y pairs
            for i in range(0, len(numbers) - 1, 2):
                x, y = numbers[i], numbers[i + 1]
                points.append((x, y))
        elif command == "H":                       # horizontal line: only x changes
            for n in numbers:
                x = n
                points.append((x, y))
        elif command == "V":                       # vertical line: only y changes
            for n in numbers:
                y = n
                points.append((x, y))
    return points


def _element_points(element):
    """Extreme points of one element: if these are inside the viewBox, the shape is too."""
    name = local_name(element.tag)

    if name == "rect":
        values = [_number(element, "x"), _number(element, "y"),
                  _number(element, "width"), _number(element, "height")]
        if None in values:
            return []
        x, y, w, h = values
        return [(x, y), (x + w, y + h)]

    if name == "circle":
        values = [_number(element, "cx"), _number(element, "cy"), _number(element, "r")]
        if None in values:
            return []
        cx, cy, r = values
        return [(cx - r, cy - r), (cx + r, cy + r)]

    if name == "ellipse":
        values = [_number(element, "cx"), _number(element, "cy"),
                  _number(element, "rx"), _number(element, "ry")]
        if None in values:
            return []
        cx, cy, rx, ry = values
        return [(cx - rx, cy - ry), (cx + rx, cy + ry)]

    if name == "line":
        values = [_number(element, "x1"), _number(element, "y1"),
                  _number(element, "x2"), _number(element, "y2")]
        if None in values:
            return []
        return [(values[0], values[1]), (values[2], values[3])]

    if name in ("polygon", "polyline"):
        return _points_from_list(element.get("points", ""))

    if name == "text":                             # we check the anchor point only, not text width
        x, y = _number(element, "x"), _number(element, "y")
        if x is None or y is None:
            return []
        return [(x, y)]

    if name == "path":
        points = _path_points(element.get("d", ""))
        return points if points is not None else []

    return []                                      # other elements (g, title, animate...) have no geometry


def _collect_problems(element, bounds, problems):
    """Walk the tree and record every element that reaches outside the bounds."""
    name = local_name(element.tag)
    if name in SKIP_CONTAINERS:
        return
    if element.get("transform") is not None:       # cannot evaluate: skip this element and its children
        return

    left, top, right, bottom = bounds
    for x, y in _element_points(element):
        if x < left or x > right or y < top or y > bottom:
            problems.append(f"<{name}> reaches ({x:g}, {y:g})")
            break                                  # one report per element is enough

    for child in element:                          # now check the children
        _collect_problems(child, bounds, problems)


def in_viewbox(svg_text):
    """Pass if no drawn element extends outside the viewBox."""
    root = parse_svg(svg_text)
    viewbox = parse_viewbox(root.get("viewBox"))
    if viewbox is None:
        return False, 'The <svg> has no valid viewBox attribute (expected viewBox="0 0 800 600").'

    min_x, min_y, width, height = viewbox
    bounds = (min_x, min_y, min_x + width, min_y + height)   # left, top, right, bottom

    problems = []
    _collect_problems(root, bounds, problems)
    if problems:
        shown = "; ".join(problems[:5])            # keep the message short for the retry prompt
        extra = f" (and {len(problems) - 5} more)" if len(problems) > 5 else ""
        return False, (f"{len(problems)} element(s) are outside the viewBox "
                       f"{min_x:g} {min_y:g} {width:g} {height:g}: {shown}{extra}.")
    return True, "Everything is inside the viewBox."

