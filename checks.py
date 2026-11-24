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