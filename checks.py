# checks.py
# Automatic checks on the SVG the model returns.
# Every check is a small function that returns (passed: bool, reason: str).
# The reason text is also fed back to the model if a retry is needed.

import re                                   # used in Steps 8 and 9 (path and number parsing)
from svgelements import Matrix, Point, Rect, Circle, Ellipse, SimpleLine, Polygon, Polyline, Path
import xml.etree.ElementTree as ET          # Python's built-in XML parser
import config                               # for MIN_TEXT_LABELS
from svg_utils import parse_viewbox, to_float   # used in Step 8
from render_bounds import rendered_bounds


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


# Elements inside these containers do not render directly.
NON_RENDERED = {"defs", "symbol", "clipPath", "mask", "pattern", "marker", "metadata", "style", "title", "desc"}


def _hidden(element, hidden_selectors=()):
    style = element.get("style", "").lower().replace(" ", "")
    css_hidden = any((selector.startswith(".") and selector[1:] in element.get("class", "").split())
                     or (selector.startswith("#") and selector[1:] == element.get("id"))
                     or (not selector.startswith((".", "#")) and selector == local_name(element.tag))
                     for selector in hidden_selectors)
    return (css_hidden or element.get("display", "").lower() == "none"
            or element.get("visibility", "").lower() in ("hidden", "collapse")
            or "display:none" in style or "visibility:hidden" in style
            or element.get("opacity", "").strip() == "0"
            or "opacity:0;" in style or style.endswith("opacity:0"))


def rendered_elements(root):
    """Yield directly rendered elements, excluding hidden/non-rendered subtrees.

    CSS selectors and referenced <use> instances need a browser to resolve fully.
    """
    hidden_selectors = set()
    css = "\n".join("".join(e.itertext()) for e in root.iter() if local_name(e.tag) == "style")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if re.search(r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))\s*(?:;|$)", body, re.I):
            hidden_selectors.update(part.strip() for part in selector.split(",") if re.fullmatch(r"(?:[\w-]+|\.[\w-]+|#[\w-]+)", part.strip()))
    def visit(element):
        if local_name(element.tag) in NON_RENDERED or _hidden(element, hidden_selectors):
            return
        yield element
        for child in element:
            yield from visit(child)
    return visit(root)


def title_and_labels(svg_text):
    """Require a direct title and at least MIN_TEXT_LABELS directly rendered labels."""
    root = parse_svg(svg_text)
    title_text = next(((child.text or "").strip() for child in root
                       if local_name(child.tag) == "title" and (child.text or "").strip()), "")
    label_count = sum(1 for element in rendered_elements(root)
                      if local_name(element.tag) == "text" and "".join(element.itertext()).strip())
    problems = []
    if not title_text:
        problems.append("there is no non-empty <title> directly inside <svg>")
    if label_count < config.MIN_TEXT_LABELS:
        problems.append(f"there are only {label_count} visible <text> labels, at least {config.MIN_TEXT_LABELS} are needed")
    if problems:
        return False, "Problems: " + "; ".join(problems) + "."
    return True, f"Title found and {label_count} directly rendered text labels."


# ---------- Check 3: has at least one animation ----------
ANIMATION_TAGS = ("animate", "animateTransform", "animateMotion", "set")


def _valid_duration(value):
    if not value:
        return False
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?|\.\d+)\s*(ms|s|min|h)?\s*", value)
    return bool(match and float(match.group(1)) > 0)


def _smil_changes(element):
    name = local_name(element.tag)
    if name not in ANIMATION_TAGS or not _valid_duration(element.get("dur")):
        return False
    if name == "animateMotion":
        return bool(element.get("path", "").strip() or any(local_name(c.tag) == "mpath" and (c.get("href") or c.get("{http://www.w3.org/1999/xlink}href")) for c in element))
    if not element.get("attributeName"):
        return False
    if name == "set":
        return element.get("to") is not None
    values = [v.strip() for v in element.get("values", "").split(";") if v.strip()]
    return (len(set(values)) >= 2 or
            (element.get("from") is not None and element.get("to") is not None
             and element.get("from") != element.get("to")) or
            (element.get("by") not in (None, "", "0")))


def has_animation(svg_text):
    """Check for a timed SMIL change or a referenced CSS keyframes animation.

    This is a structural check, not proof of actual browser playback.
    """
    root = parse_svg(svg_text)
    visible = list(rendered_elements(root))
    for element in visible:
        if _smil_changes(element):
            return True, f"Found a timed <{local_name(element.tag)}> animation."
    css = "\n".join("".join(e.itertext()) for e in root.iter() if local_name(e.tag) == "style")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    names = set()
    for match in re.finditer(r"@(?:-webkit-)?keyframes\s+([\w-]+)\s*\{", css, re.I):
        depth, end = 1, match.end()
        while end < len(css) and depth:
            depth += (css[end] == "{") - (css[end] == "}")
            end += 1
        frames = re.findall(r"(?:from|to|[\d.]+%)\s*\{([^{}]*)\}", css[match.end():end-1], re.I)
        if len(frames) >= 2 and len({re.sub(r"\s+", "", frame) for frame in frames}) >= 2:
            names.add(match.group(1))
    # A simple selector, referring to a rendered element, must use the keyframe.
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "@" in selector:
            continue
        declarations = re.findall(r"(?:^|;)\s*(?:-webkit-)?animation(?:-name)?\s*:\s*([^;]+)", body, re.I)
        durations = re.findall(r"(?:^|;)\s*(?:-webkit-)?animation-duration\s*:\s*([^;]+)", body, re.I)
        def active_duration(value):
            times = re.findall(r"(?<![\w.-])(?:\d+(?:\.\d+)?|\.\d+)\s*(?:ms|s)\b", value, re.I)
            return bool(times and _valid_duration(times[0].lower()))
        if not any(re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", value)
                   and (active_duration(value) or any(active_duration(duration) for duration in durations))
                   for value in declarations for name in names):
            continue
        for part in selector.split(","):
            part = part.strip()
            if not re.fullmatch(r"(?:[\w-]+|\.[\w-]+|\#[\w-]+)", part):
                continue
            for element in visible:
                if (part.startswith(".") and part[1:] in element.get("class", "").split()
                    or part.startswith("#") and part[1:] == element.get("id")
                    or not part.startswith((".", "#")) and part == local_name(element.tag)):
                    return True, "Found a CSS keyframes animation referenced by a rendered element."
    return False, "No valid timed animation found on a directly rendered element."


# ---------- Check 4: static geometry against the viewBox ----------
# SVG text metrics, CSS, references and animation require a browser renderer.
# This check does not claim to prove those cases are inside the bounds.
GEOMETRY = {"rect": Rect, "circle": Circle, "ellipse": Ellipse, "line": SimpleLine,
            "polygon": Polygon, "polyline": Polyline, "path": Path}


def _collect_problems(element, bounds, problems, transform=None):
    name = local_name(element.tag)
    if name in NON_RENDERED or _hidden(element):
        return
    try:
        current = Matrix(element.get("transform", ""))
        if transform is not None:
            # SVG child coordinates are transformed by the child, then the parent.
            current *= transform
        numeric_attrs = {"x", "y", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "width", "height", "stroke-width"}
        unsupported_units = any(attr in numeric_attrs and to_float(value) is None
                                for attr, value in element.attrib.items())
        if name in GEOMETRY and not unsupported_units and not any(local_name(child.tag) == "animateMotion" for child in element):
            shape = GEOMETRY[name](dict(element.attrib))
            shape *= current
            box = shape.bbox(with_stroke=True)
            if box is not None:
                left, top, right, bottom = bounds
                if box[0] < left - 1e-9 or box[1] < top - 1e-9 or box[2] > right + 1e-9 or box[3] > bottom + 1e-9:
                    problems.append(f"<{name}> reaches bounds ({box[0]:g}, {box[1]:g}, {box[2]:g}, {box[3]:g})")
        elif name == "text":
            # The text anchor can be checked, but its rendered extent cannot.
            x, y = to_float(element.get("x", "0")), to_float(element.get("y", "0"))
            if x is not None and y is not None:
                point = Point(x, y) * current
                left, top, right, bottom = bounds
                if point.x < left or point.x > right or point.y < top or point.y > bottom:
                    problems.append(f"<text> anchor reaches ({point.x:g}, {point.y:g})")
    except (ValueError, TypeError, AttributeError, ZeroDivisionError, OverflowError) as error:
        problems.append(f"<{name}> geometry could not be evaluated: {error}")
        return
    for child in element:
        _collect_problems(child, bounds, problems, current)


def in_viewbox(svg_text):
    """Check supported static shape bounds; dynamic/browser-only content needs review."""
    root = parse_svg(svg_text)
    viewbox = parse_viewbox(root.get("viewBox"))
    if viewbox is None:
        return False, 'The <svg> has no valid viewBox with finite, positive width and height.'
    min_x, min_y, width, height = viewbox
    bounds = (min_x, min_y, min_x + width, min_y + height)
    problems = []
    _collect_problems(root, bounds, problems)
    if problems:
        shown = "; ".join(problems[:5])
        extra = f" (and {len(problems) - 5} more)" if len(problems) > 5 else ""
        return False, (f"{len(problems)} element(s) are outside or could not be checked against the viewBox "
                       f"{min_x:g} {min_y:g} {width:g} {height:g}: {shown}{extra}.")
    return True, ("Supported static geometry and text anchors are inside the viewBox. "
                  "Text extent, CSS, references and animation still require visual review.")


# ---------- Check 5 (my own): custom_checks = concept keywords + safety ----------
# Spelling alternatives so a correct diagram is not rejected unfairly.
# Careful: 'o2' is NOT allowed as oxygen because it would match inside 'co2'.
SYNONYMS = {
    "centre": ["centre", "center"],
    "carbon dioxide": ["carbon dioxide", "co2", "co\u2082"],
}


def concept_keywords(svg_text, concept):
    """Pass if every required keyword for this concept appears in the <text> labels."""
    root = parse_svg(svg_text)
    pieces = []
    for element in rendered_elements(root):
        if local_name(element.tag) == "text":
            pieces.append("".join(element.itertext()))
    all_text = " ".join(pieces).lower()            # lowercase so matching ignores capitals

    missing = []
    for keyword in concept["keywords"]:
        options = SYNONYMS.get(keyword, [keyword])
        found = False
        for option in options:
            if option in all_text:
                found = True
        if not found:
            missing.append(keyword)

    if missing:
        return False, "The labels never mention: " + ", ".join(missing) + "."
    return True, "All required keywords are present."


FORBIDDEN_TAGS = ("script", "foreignObject", "iframe", "object", "embed")


def safe_svg(svg_text):
    """Pass if the SVG has nothing that could run code or load outside content."""
    root = parse_svg(svg_text)
    problems = []
    for element in root.iter():
        name = local_name(element.tag)
        if name in FORBIDDEN_TAGS:
            problems.append(f"forbidden <{name}> element")
        for attribute, value in element.attrib.items():
            attr = local_name(attribute).lower()
            if attr.startswith("on"):              # onclick, onload, onbegin ... = event handlers
                problems.append(f"event attribute '{attr}' on <{name}>")
            if attr == "href" and not value.strip().startswith("#"):   # only '#id' links are allowed
                problems.append(f"external link in href on <{name}>")
        if name == "style":
            css = (element.text or "").lower()
            if "@import" in css or "http" in css:
                problems.append("external resource in <style>")
    if problems:
        return False, "Unsafe content: " + "; ".join(problems[:5]) + "."
    return True, "No scripts, event handlers or external links."


def custom_checks(svg_text, concept):
    """My 5th check: groups the keyword check and the safety check into one."""
    keywords_ok, keywords_reason = concept_keywords(svg_text, concept)
    safe_ok, safe_reason = safe_svg(svg_text)

    reasons = []
    if not keywords_ok:
        reasons.append(keywords_reason)
    if not safe_ok:
        reasons.append(safe_reason)
    if reasons:
        return False, " ".join(reasons)
    return True, "Keywords present and SVG is safe."


# ---------- Run everything ----------
def _pack(result):
    """Turn a (passed, reason) tuple into a dict that can be saved as JSON."""
    return {"passed": result[0], "reason": result[1]}


def _bounds_need_rendering(root):
    # These constructs or values cannot be bounded reliably by the static shape parser.
    uncertain = {"text", "use", "image", "foreignObject", "animate", "animateTransform",
                 "animateMotion", "set", "style", "clipPath", "mask", "pattern", "marker", "filter"}
    ignored = NON_RENDERED | {"svg", "g", "a", "switch"}
    for element in root.iter():
        name = local_name(element.tag)
        if name in uncertain or (name not in GEOMETRY and name not in ignored):
            return True
        if any(local_name(key) in {"style", "class", "filter", "clip-path", "mask", "marker-start", "marker-mid", "marker-end"}
               or (local_name(key) in {"x", "y", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "width", "height", "stroke-width"}
                   and to_float(value) is None)
               for key, value in element.attrib.items()):
            return True
    return False


def _renderer_needs_browser(root):
    """Relative geometry depends on the original viewport, which padding changes."""
    numeric = {"x", "y", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "width", "height", "stroke-width"}
    relative_css = re.compile(
        r"(?:^|[;{])\s*(?:x|y|cx|cy|r|rx|ry|width|height|stroke-width|font-size|transform|transform-origin)"
        r"\s*:\s*[^;}]*?(?:%|(?:vw|vh|vmin|vmax)\b|var\s*\()", re.I)
    for element in root.iter():
        if local_name(element.tag) in GEOMETRY or local_name(element.tag) == "text":
            if any(local_name(key) in numeric and to_float(value) is None for key, value in element.attrib.items()):
                return True
        css = element.get("style", "")
        if local_name(element.tag) == "style":
            css += " ".join(element.itertext())
        if relative_css.search(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
            return True
    return False

def run_all_checks(svg_text, concept):
    """Run the automatic checks. Returns {check_name: {"passed": bool, "reason": str}}."""
    results = {}
    results["valid_xml"] = _pack(valid_xml(svg_text))

    if not results["valid_xml"]["passed"]:
        # The other checks need a parsed SVG, so mark them as skipped failures.
        for name in ("in_viewbox", "animated_bounds", "title_and_labels", "has_animation", "custom_checks"):
            results[name] = {"passed": False, "reason": "Skipped because the SVG could not be parsed."}
        return results

    results["in_viewbox"] = _pack(in_viewbox(svg_text))
    root = parse_svg(svg_text)
    if results["in_viewbox"]["passed"] and _bounds_need_rendering(root):
        # Rasterise only safe SVGs. A static raster cannot certify moving content.
        if _renderer_needs_browser(root):
            results["in_viewbox"] = {"passed": None, "reason": "Viewport-relative geometry needs browser-based review."}
        elif safe_svg(svg_text)[0]:
            passed, reason = rendered_bounds(svg_text)
            results["in_viewbox"] = {"passed": passed, "reason": reason}
        else:
            results["in_viewbox"] = {"passed": None, "reason": "Static rendering skipped for unsafe SVG."}
    has_dynamic_content = any(local_name(e.tag) in ANIMATION_TAGS for e in root.iter()) or any(
        "@keyframes" in "".join(e.itertext()).lower() for e in root.iter() if local_name(e.tag) == "style")
    results["animated_bounds"] = ({"passed": None, "reason": "Animation movement and animated visibility need browser playback review; the renderer checks a static snapshot only."}
                                  if has_dynamic_content else {"passed": True, "reason": "No animated movement to check."})
    results["title_and_labels"] = _pack(title_and_labels(svg_text))
    results["has_animation"] = _pack(has_animation(svg_text))
    results["custom_checks"] = _pack(custom_checks(svg_text, concept))
    return results


def failed_checks(results):
    """List actual failures; skipped and unverified checks are not failures."""
    failures = []
    for name, outcome in results.items():
        if outcome["passed"] is False and not outcome["reason"].startswith("Skipped"):
            failures.append((name, outcome["reason"]))
    return failures

