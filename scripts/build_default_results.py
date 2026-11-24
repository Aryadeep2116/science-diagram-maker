"""Build deterministic, hand-authored SVG examples without an API request.

Review notes are an AI assistant's source/visual assessment, not a user's or an
expert's approval. Regenerate with `python scripts/build_default_results.py`.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from concepts import CONCEPTS
from verification import assess_result, svg_digest


def start(title, subtitle, desc):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" role="img">
<title>{title}</title><desc>{desc}</desc>
<rect x="8" y="8" width="784" height="584" rx="22" fill="#f6f8fc"/>
<text x="44" y="55" font-family="DejaVu Sans" font-size="26" font-weight="bold" fill="#14233f">{title}</text>
<text x="44" y="83" font-family="DejaVu Sans" font-size="15" fill="#52637a">{subtitle}</text>
<rect x="30" y="106" width="740" height="403" rx="20" fill="#ffffff" stroke="#e1e7f0" stroke-width="2"/>
'''


def text(x, y, value, size=16, color='#243851', anchor='start', weight='normal'):
    return f'<text x="{x}" y="{y}" font-family="DejaVu Sans" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{value}</text>\n'


def moving_dot(path, color, duration, begin="0s", radius=5, kind="flow"):
    """Animate a marker along a concrete path; motion is illustrative, not to scale."""
    return (f'<circle cx="0" cy="0" r="{radius}" fill="{color}" stroke="#ffffff" stroke-width="1.5" data-motion="{kind}">'
            f'<animateMotion path="{path}" dur="{duration}" begin="{begin}" '
            'calcMode="linear" repeatCount="indefinite"/></circle>\n')


def footer(line):
    return f'<rect x="30" y="526" width="740" height="48" rx="12" fill="#eaf0fa"/>{text(400, 556, line, 17, "#243a5a", "middle", "bold")}</svg>'


def pythagoras():
    s = start('Pythagoras’ theorem', 'A relationship between the sides of a right triangle', 'Dots trace the three sides of a right triangle. Squares on the sides show that nine plus sixteen equals twenty-five square units.')
    s += f'''<polygon points="320,265 320,355 230,355 230,265" fill="#dbeafe" stroke="#3b82f6" stroke-width="3"/>
<polygon points="320,355 440,355 440,475 320,475" fill="#d1fae5" stroke="#10b981" stroke-width="3"/>
<polygon points="320,265 440,355 530,235 410,145" fill="#fce7df" stroke="#e7704f" stroke-width="3"/>
<polygon points="320,265 320,355 440,355" fill="#ffffff" stroke="#253653" stroke-width="3"/>
<path d="M320 337 H338 V355" fill="none" stroke="#253653" stroke-width="2"/>
'''
    s += text(275, 304, 'a² = 9', 17, '#1d4ed8', 'middle', 'bold') + text(275, 325, 'square units', 11, '#1d4ed8', 'middle')
    s += text(380, 410, 'b² = 16', 17, '#047857', 'middle', 'bold') + text(380, 433, 'square units', 11, '#047857', 'middle')
    s += text(425, 245, 'c² = 25', 17, '#b84a30', 'middle', 'bold') + text(425, 267, 'square units', 11, '#b84a30', 'middle')
    s += text(329, 314, '3', 15, '#253653') + text(376, 348, '4', 15, '#253653', 'middle')
    s += text(554, 370, 'Hypotenuse c = 5', 15, '#b84a30', 'start', 'bold')
    s += '<path d="M548 365 L425 344" stroke="#b84a30" stroke-width="2" fill="none"/>'
    s += moving_dot('M320 265 L320 355 L320 265', '#2563eb', '4s', kind='side-a')
    s += moving_dot('M320 355 L440 355 L320 355', '#059669', '4s', kind='side-b')
    s += moving_dot('M320 265 L440 355 L320 265', '#cf5837', '4s', kind='hypotenuse')
    s += text(605, 440, 'Dots trace each side', 14, '#52637a', 'middle')
    return s + footer('a² + b² = c²     ·     9 + 16 = 25')


def circle():
    s = start('Parts of a circle', 'A radius sweeps around the centre', 'The radius rotates around the centre and its endpoint traces the circumference. The diameter through the centre is twice the radius.')
    s += '''<circle cx="260" cy="300" r="150" fill="#f0f6ff" stroke="#395fc4" stroke-width="7"/>
<line x1="110" y1="300" x2="410" y2="300" stroke="#0d9b82" stroke-width="5"/>
<g data-motion="rotating-radius">
  <line x1="260" y1="300" x2="350" y2="180" stroke="#ea8b32" stroke-width="5"/>
  <circle cx="350" cy="180" r="7" fill="#ea8b32" stroke="#ffffff" stroke-width="1.5"/>
  <animateTransform attributeName="transform" type="rotate" from="0 260 300" to="360 260 300" dur="8s" repeatCount="indefinite"/>
</g>
<circle cx="260" cy="300" r="7" fill="#263b5c"/>
'''
    for y, color, heading, detail in [(190,'#263b5c','Centre','The fixed middle point'),(245,'#ea8b32','Radius','Centre to circumference'),(300,'#0d9b82','Diameter','Across the centre: 2 radii'),(355,'#395fc4','Circumference','Path traced by the endpoint')]:
        s += f'<circle cx="472" cy="{y-6}" r="7" fill="{color}"/>' + text(491,y,heading,16,color,'start','bold') + text(491,y+22,detail,13,'#52637a')
    return s + footer('Diameter = 2 × radius')


def circuit():
    s = start('Series circuit', 'One closed loop · the same current everywhere', 'Moving markers represent conventional current in a complete loop. They move from the positive cell terminal through both lamps and return to the negative terminal; marker speed is illustrative.')
    s += '''<path d="M200 335 V255 H290 M350 255 H450 M510 255 H640 V430 H200 V365" fill="none" stroke="#243851" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>
<line x1="174" y1="335" x2="226" y2="335" stroke="#243851" stroke-width="5"/>
<line x1="185" y1="365" x2="215" y2="365" stroke="#243851" stroke-width="5"/>
<circle cx="320" cy="255" r="30" fill="#fff9df" stroke="#243851" stroke-width="4"/>
<circle cx="480" cy="255" r="30" fill="#fff9df" stroke="#243851" stroke-width="4"/>
<path d="M301 236 L339 274 M339 236 L301 274 M461 236 L499 274 M499 236 L461 274" stroke="#d89512" stroke-width="3"/>
'''
    # Evenly spaced markers show conventional current, not electron drift.
    for x in (405, 580):
        s += f'<path d="M{x-18} 255 H{x+17} M{x+8} 247 L{x+17} 255 L{x+8} 263" fill="none" stroke="#3974db" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    loop = 'M200 335 V255 H640 V430 H200 V365 V335'
    for begin in ('0s', '-2s', '-4s', '-6s'):
        s += moving_dot(loop, '#3974db', '8s', begin, radius=5, kind='conventional-current')
    s += text(320, 205, 'Lamp 1', 16, '#243851', 'middle', 'bold') + text(480, 205, 'Lamp 2', 16, '#243851', 'middle', 'bold')
    s += text(128, 354, 'Cell', 16, '#243851', 'middle', 'bold') + text(242, 342, '+', 18, '#cc5950') + text(235, 372, '−', 18, '#52637a')
    s += text(420, 394, 'Markers show conventional current direction', 16, '#3974db', 'middle', 'bold')
    return s + footer('Cell voltage = voltage across lamp 1 + lamp 2')


def photosynthesis():
    s = start('Photosynthesis', 'Plants use light energy to make glucose', 'Carbon dioxide and water enter the leaf. Light energy absorbed by chlorophyll supports production of glucose and oxygen.')
    s += '''<path d="M290 324 C290 241 367 205 432 226 C475 240 510 275 510 311 C490 368 420 397 361 382 C326 374 301 354 290 324 Z" fill="#d9f5d5" stroke="#398c5c" stroke-width="4"/>
<path d="M310 342 C357 323 416 300 484 258 M359 323 L344 286 M395 307 L385 270 M419 299 L445 323" fill="none" stroke="#398c5c" stroke-width="3"/>
'''
    s += '<circle cx="400" cy="158" r="23" fill="#fbd466" stroke="#e4a92c" stroke-width="3"/>'
    s += '<path d="M400 189 V218 M392 210 L400 218 L408 210" stroke="#e4a92c" stroke-width="4" fill="none"/>'
    # Separate paths and arrowheads, avoiding SVG markers and keeping all extents explicit.
    for d in ('M184 264 H281 M270 256 L281 264 L270 272', 'M184 364 H281 M270 356 L281 364 L270 372', 'M520 264 H615 M604 256 L615 264 L604 272', 'M520 364 H615 M604 356 L615 364 L604 372'):
        s += f'<path d="{d}" fill="none" stroke="#5683c0" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    for path, color, kind in [('M184 264 H281', '#5683c0', 'carbon-dioxide-in'),
                              ('M184 364 H281', '#5683c0', 'water-in'),
                              ('M520 264 H615', '#5683c0', 'oxygen-out'),
                              ('M520 364 H615', '#5683c0', 'glucose-out'),
                              ('M400 189 V218', '#e4a92c', 'light-in')]:
        s += moving_dot(path, color, '2.5s', radius=5, kind=kind)
    s += text(452, 163, 'Light energy', 14, '#966610', 'start', 'bold')
    s += text(400, 415, 'Leaf contains chlorophyll', 15, '#246941', 'middle', 'bold')
    s += text(105, 253, 'Carbon dioxide', 14, '#243851', 'middle', 'bold') + text(105, 353, 'Water', 14, '#243851', 'middle', 'bold')
    s += text(684, 253, 'Oxygen', 14, '#243851', 'middle', 'bold') + text(684, 353, 'Glucose', 14, '#243851', 'middle', 'bold')
    s += text(400, 475, 'Moving dots show direction, not actual speed or scale', 13, '#52637a', 'middle')
    return s + footer('Carbon dioxide + water  →  glucose + oxygen')


def states():
    s = start('States of matter', 'Particle models: spacing and movement', 'Solid particles are closely packed and vibrate; liquid particles are close and move past one another; gas particles are far apart and move freely.')
    colors = ['#507cde','#0da68b','#d9893e']
    for x, label, color in [(50,'SOLID',colors[0]),(293,'LIQUID',colors[1]),(536,'GAS',colors[2])]:
        s += f'<rect x="{x}" y="143" width="214" height="287" rx="15" fill="#f7f9fd" stroke="#e1e7f0" stroke-width="2"/>'
        s += text(x+107,176,label,16,color,'middle','bold')
        s += f'<rect x="{x+20}" y="198" width="174" height="165" rx="8" fill="#ffffff" stroke="#c9d5e4" stroke-width="2"/>'
    # Solid particles make tiny local vibrations about fixed lattice positions.
    for row in range(4):
        for col in range(4):
            x, y = 108 + col*31, 228 + row*34
            delta = 2 if (row + col) % 2 else -2
            path = f'M{x} {y} l{delta} 0 l{-2*delta} 0 l{delta} 0'
            s += moving_dot(path, colors[0], '0.7s', radius=11, kind='solid-vibration')
    # Neighbouring closely packed rows slide in opposite directions so that
    # particles move past each other without overlapping. This is illustrative.
    for row in range(4):
        for col in range(4):
            x = 350 + col*30 + (4 if row % 2 else 0)
            y = 227 + row*30 + (1 if col % 2 else 0)
            dx = 7 if row % 2 == 0 else -7
            path = f'M{x} {y} l{dx} 0 l{-2*dx} 0 l{dx} 0'
            s += moving_dot(path, colors[1], '3.2s', begin=f'-{row*0.3}s', radius=11, kind='liquid-exchange')
    # Gas particles traverse larger, separated paths more quickly than liquid.
    for i, (x, y) in enumerate([(580,235),(645,235),(710,235),(580,320),(645,320),(710,320)]):
        dx, dy = (13 if i % 2 == 0 and x < 700 else -13), (10 if i < 3 else -10)
        path = f'M{x} {y} l{dx} {dy} l{-dx} {-dy}'
        s += moving_dot(path, colors[2], '1.4s', radius=10, kind='gas-motion')
    s += text(157,392,'Close, ordered',14,'#435875','middle','bold') + text(157,413,'Vibrate in place',13,'#52637a','middle')
    s += text(400,392,'Close, irregular',14,'#435875','middle','bold') + text(400,413,'Move past each other',13,'#52637a','middle')
    s += text(643,392,'Far apart',14,'#435875','middle','bold') + text(643,413,'Move freely and fast',13,'#52637a','middle')
    s += text(400, 474, 'Motion is a simplified model, not to scale.', 14, '#52637a','middle')
    return s + footer('Heating can change how particles are arranged and move')


REASONS = [
    'The 3–4–5 triangle is right-angled; moving markers trace its sides, and the square areas are 9, 16 and 25 square units.',
    'The radius rotates about the centre with its endpoint on the circumference; the diameter through the centre is twice the radius.',
    'Both lamps and the cell form one loop; markers show conventional current direction, not electron flow or actual speed. Lamp voltages sum to cell voltage.',
    'Moving markers show carbon dioxide and water entering, light arriving, and oxygen and glucose leaving; the word equation is simplified.',
    'Solid particles vibrate about fixed positions; liquid particles slide past each other while close; gas particles are widely spaced and move faster in this simplified model.',
]


def build_results():
    """Rebuild illustrations with the original runs' metrics, clearly attributed."""
    metrics = json.loads((ROOT / 'data' / 'original_generation_metrics.json').read_text(encoding='utf-8'))
    diagrams = [pythagoras(), circle(), circuit(), photosynthesis(), states()]
    results = []
    for concept, svg, reason in zip(CONCEPTS, diagrams, REASONS):
        review = {'status': 'pass', 'reason': reason, 'svg_sha256': svg_digest(svg),
                  'method': 'AI assistant assessment of SVG geometry, labels and sampled animation; not independent expert or user approval.'}
        previous_run = dict(metrics[str(concept['id'])])
        previous_svg_digest = previous_run.pop('svg_sha256')
        result = assess_result({'id': concept['id'], 'name': concept['name'], 'subject': concept['subject'],
            'svg': svg, **previous_run,
            'metrics_source': 'previous_gemini_run', 'metrics_svg_sha256': previous_svg_digest,
            'illustration_source': 'built-in',
            'note': 'Metrics describe an earlier Gemini-generated SVG, not this built-in illustration.',
            'scientific_verification': review}, concept)
        results.append(result)
    return results


def main():
    results = build_results()
    (ROOT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for result in results:
        print(result['id'], result['final_status'], [(k, v['reason']) for k, v in result['checks'].items() if v['passed'] is not True])


if __name__ == '__main__':
    main()
