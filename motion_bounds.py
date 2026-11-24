"""Conservative all-time bounds for a small, explicit subset of SVG motion.

This is not an SVG animation interpreter. Unknown elements, styling, transforms,
paths or animation options return False (not certified), never a forced pass.
"""
import math
import re

from svg_utils import parse_viewbox, to_float

_TOKEN = re.compile(r'[MmLlHhVv]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
_SECONDS = re.compile(r'-?(?:\d+(?:\.\d+)?|\.\d+)s\Z')
_DRAWABLES = {'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'path'}
_ALLOWED = _DRAWABLES | {'svg', 'g', 'text', 'title', 'desc', 'animateMotion', 'animateTransform'}


def _name(element):
    return element.tag.split('}', 1)[-1]


def _number(element, name):
    result = to_float(element.get(name))
    if result is None or not math.isfinite(result):
        raise ValueError('Expected an absolute finite numeric attribute')
    return result


def linear_path_bounds(path):
    """Return bounds of a strictly parsed M/L/H/V path, or None if unsupported.

    Straight segments lie inside the bounding rectangle of their endpoints.
    Curves, arcs, closepath, malformed data, and non-finite values are rejected.
    """
    if not path or len(path) > 16000:
        return None
    tokens, end = [], 0
    for match in _TOKEN.finditer(path):
        if not re.fullmatch(r'[\s,]*', path[end:match.start()]):
            return None
        tokens.append(match.group())
        end = match.end()
    if not tokens or not re.fullmatch(r'[\s,]*', path[end:]):
        return None
    x = y = 0.0
    points = []
    command = None
    i = 0
    first = True
    try:
        while i < len(tokens):
            if len(tokens[i]) == 1 and tokens[i] in 'MmLlHhVv':
                command = tokens[i]
                i += 1
                if i == len(tokens) or tokens[i] in 'MmLlHhVv':
                    return None
            if command is None or (first and command not in 'Mm'):
                return None
            first = False
            count = 2 if command.upper() in ('M', 'L') else 1
            if i + count > len(tokens):
                return None
            values = [float(n) for n in tokens[i:i + count]]
            if not all(math.isfinite(v) for v in values):
                return None
            i += count
            relative = command.islower()
            kind = command.upper()
            if kind in ('M', 'L'):
                x, y = ((x + values[0], y + values[1]) if relative else (values[0], values[1]))
            elif kind == 'H':
                x = x + values[0] if relative else values[0]
            else:
                y = y + values[0] if relative else values[0]
            if not math.isfinite(x) or not math.isfinite(y):
                return None
            points.append((x, y))
            if kind == 'M':
                command = 'l' if relative else 'L'
    except (ValueError, OverflowError):
        return None
    if len(points) < 2:
        return None
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def _inside(bounds, viewbox, padding):
    x, y, width, height = viewbox
    left, top, right, bottom = bounds
    return (left - padding >= x and top - padding >= y
            and right + padding <= x + width and bottom + padding <= y + height)


def _motion_circle(circle, animation, viewbox):
    if (set(circle.attrib) - {'cx', 'cy', 'r', 'fill', 'stroke', 'stroke-width', 'data-motion'}
            or set(animation.attrib) - {'path', 'dur', 'begin', 'calcMode', 'repeatCount'}
            or len(animation) or len(circle) != 1
            or animation.get('calcMode', 'paced') not in ('linear', 'paced')
            or animation.get('repeatCount') != 'indefinite'
            or not _SECONDS.fullmatch(animation.get('dur', ''))
            or float(animation.get('dur')[:-1]) <= 0
            or not _SECONDS.fullmatch(animation.get('begin', '0s'))):
        return False
    if _number(circle, 'cx') != 0 or _number(circle, 'cy') != 0:
        return False
    radius, stroke = _number(circle, 'r'), _number(circle, 'stroke-width')
    if radius <= 0 or stroke < 0 or not circle.get('stroke'):
        return False
    bounds = linear_path_bounds(animation.get('path'))
    # Full stroke width (rather than half) is a conservative margin.
    return bounds is not None and _inside(bounds, viewbox, radius + stroke)


def _rotation_group(group, animation, viewbox):
    if (set(group.attrib) - {'data-motion'}
            or set(animation.attrib) - {'attributeName', 'type', 'from', 'to', 'dur', 'repeatCount'}
            or animation.get('attributeName') != 'transform' or animation.get('type') != 'rotate'
            or animation.get('repeatCount') != 'indefinite'
            or not _SECONDS.fullmatch(animation.get('dur', ''))
            or float(animation.get('dur')[:-1]) <= 0 or len(animation)):
        return False
    try:
        start = [float(n) for n in animation.get('from', '').replace(',', ' ').split()]
        end = [float(n) for n in animation.get('to', '').replace(',', ' ').split()]
        if (len(start) != 3 or len(end) != 3 or not all(math.isfinite(n) for n in start + end)
                or start[1:] != end[1:]):
            return False
        cx, cy = start[1:]
        shapes = [node for node in group if node is not animation]
        if not shapes:
            return False
        extent = 0.0
        for node in shapes:
            if len(node) or not node.get('stroke'):
                return False
            width = _number(node, 'stroke-width')
            if width < 0:
                return False
            if _name(node) == 'line' and not (set(node.attrib) - {'x1', 'y1', 'x2', 'y2', 'stroke', 'stroke-width'}):
                for a, b in (('x1', 'y1'), ('x2', 'y2')):
                    extent = max(extent, math.hypot(_number(node, a) - cx, _number(node, b) - cy) + width)
            elif _name(node) == 'circle' and not (set(node.attrib) - {'cx', 'cy', 'r', 'fill', 'stroke', 'stroke-width'}):
                radius = _number(node, 'r')
                if radius <= 0:
                    return False
                extent = max(extent, math.hypot(_number(node, 'cx') - cx, _number(node, 'cy') - cy) + radius + width)
            else:
                return False
        return _inside((cx, cy, cx, cy), viewbox, extent)
    except (ValueError, OverflowError):
        return False


def bounded_motion(root):
    """Certify only circles on linear paths and fixed-centre rotating line/circle groups.

    The static raster check must also pass. This excludes CSS, references,
    nested viewports, filters, clipping, static transforms and other animation
    constructs. It says nothing about science, overlapping, or browser playback.
    """
    viewbox = parse_viewbox(root.get('viewBox'))
    if not viewbox:
        return False
    for element in root.iter():
        if (_name(element) not in _ALLOWED
                or (element is not root and _name(element) == 'svg')
                or any(k.split('}', 1)[-1] in {'style', 'transform', 'filter', 'mask', 'clip-path',
                       'marker-start', 'marker-mid', 'marker-end', 'vector-effect'} for k in element.attrib)):
            return False
    animations = [e for e in root.iter() if _name(e) in ('animateMotion', 'animateTransform')]
    if not animations:
        return False
    accepted = 0
    try:
        for parent in root:
            dynamic = [e for e in parent if _name(e) in ('animateMotion', 'animateTransform')]
            if not dynamic:
                continue
            if len(dynamic) != 1:
                return False
            anim = dynamic[0]
            if (_name(parent) == 'circle' and _name(anim) == 'animateMotion'
                    and _motion_circle(parent, anim, viewbox)):
                accepted += 1
            elif (_name(parent) == 'g' and _name(anim) == 'animateTransform'
                  and _rotation_group(parent, anim, viewbox)):
                accepted += 1
            else:
                return False
    except (ValueError, OverflowError):
        return False
    return accepted == len(animations)
