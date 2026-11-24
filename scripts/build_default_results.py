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


def pulse(delay=0):
    return f'<animate attributeName="opacity" values="1;0.35;1" dur="3s" begin="{delay}s" repeatCount="indefinite"/>'


def footer(line):
    return f'<rect x="30" y="526" width="740" height="48" rx="12" fill="#eaf0fa"/>{text(400, 556, line, 17, "#243a5a", "middle", "bold")}</svg>'


def pythagoras():
    s = start('Pythagoras’ theorem', 'A relationship between the sides of a right triangle', 'Squares on the sides of a right triangle show that nine plus sixteen equals twenty-five square units.')
    s += f'''<polygon points="320,265 320,355 230,355 230,265" fill="#dbeafe" stroke="#3b82f6" stroke-width="3">{pulse(0)}</polygon>
<polygon points="320,355 440,355 440,475 320,475" fill="#d1fae5" stroke="#10b981" stroke-width="3">{pulse(1)}</polygon>
<polygon points="320,265 440,355 530,235 410,145" fill="#fce7df" stroke="#e7704f" stroke-width="3">{pulse(2)}</polygon>
<polygon points="320,265 320,355 440,355" fill="#ffffff" stroke="#253653" stroke-width="3"/>
<path d="M320 337 H338 V355" fill="none" stroke="#253653" stroke-width="2"/>
'''
    s += text(275, 304, 'a² = 9', 17, '#1d4ed8', 'middle', 'bold') + text(275, 325, 'square units', 11, '#1d4ed8', 'middle')
    s += text(380, 410, 'b² = 16', 17, '#047857', 'middle', 'bold') + text(380, 433, 'square units', 11, '#047857', 'middle')
    s += text(425, 245, 'c² = 25', 17, '#b84a30', 'middle', 'bold') + text(425, 267, 'square units', 11, '#b84a30', 'middle')
    s += text(329, 314, '3', 15, '#253653') + text(376, 348, '4', 15, '#253653', 'middle')
    s += text(554, 370, 'Hypotenuse c = 5', 15, '#b84a30', 'start', 'bold')
    s += '<path d="M548 365 L425 344" stroke="#b84a30" stroke-width="2" fill="none"/>'
    return s + footer('a² + b² = c²     ·     9 + 16 = 25')


def circle():
    s = start('Parts of a circle', 'Four ways to describe the same circle', 'The diameter passes through the centre, a radius joins centre and circumference, and the circumference is the outer edge.')
    s += f'''<circle cx="260" cy="300" r="150" fill="#f0f6ff" stroke="#395fc4" stroke-width="7">{pulse(0)}</circle>
<line x1="110" y1="300" x2="410" y2="300" stroke="#0d9b82" stroke-width="5">{pulse(1)}</line>
<line x1="260" y1="300" x2="350" y2="180" stroke="#ea8b32" stroke-width="5">{pulse(2)}</line>
<circle cx="260" cy="300" r="7" fill="#263b5c"/>
'''
    for y, color, heading, detail in [(190,'#263b5c','Centre','The fixed middle point'),(245,'#ea8b32','Radius','Centre to circumference'),(300,'#0d9b82','Diameter','Across the centre: 2 radii'),(355,'#395fc4','Circumference','Distance around the edge')]:
        s += f'<circle cx="472" cy="{y-6}" r="7" fill="{color}"/>' + text(491,y,heading,16,color,'start','bold') + text(491,y+22,detail,13,'#52637a')
    return s + footer('Diameter = 2 × radius')


def circuit():
    s = start('Series circuit', 'One closed loop · the same current everywhere', 'A cell and two lamps are connected in one complete loop. Conventional current leaves the positive cell terminal and flows through both lamps.')
    s += '''<path d="M200 335 V255 H290 M350 255 H450 M510 255 H640 V430 H200 V365" fill="none" stroke="#243851" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>
<line x1="174" y1="335" x2="226" y2="335" stroke="#243851" stroke-width="5"/>
<line x1="185" y1="365" x2="215" y2="365" stroke="#243851" stroke-width="5"/>
<circle cx="320" cy="255" r="30" fill="#fff9df" stroke="#243851" stroke-width="4"/>
<circle cx="480" cy="255" r="30" fill="#fff9df" stroke="#243851" stroke-width="4"/>
<path d="M301 236 L339 274 M339 236 L301 274 M461 236 L499 274 M499 236 L461 274" stroke="#d89512" stroke-width="3"/>
'''
    # Conventional current arrows point from the positive (long) plate through both lamps.
    for x in (405, 580):
        s += f'<path d="M{x-18} 255 H{x+17} M{x+8} 247 L{x+17} 255 L{x+8} 263" fill="none" stroke="#3974db" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{pulse((x//100)%2)}</path>'
    s += text(320, 205, 'Lamp 1', 16, '#243851', 'middle', 'bold') + text(480, 205, 'Lamp 2', 16, '#243851', 'middle', 'bold')
    s += text(128, 354, 'Cell', 16, '#243851', 'middle', 'bold') + text(242, 342, '+', 18, '#cc5950') + text(235, 372, '−', 18, '#52637a')
    s += text(420, 394, 'Same current through both lamps', 16, '#3974db', 'middle', 'bold')
    return s + footer('Cell voltage = voltage across lamp 1 + lamp 2')


def photosynthesis():
    s = start('Photosynthesis', 'Plants use light energy to make glucose', 'Carbon dioxide and water enter the leaf. Light energy absorbed by chlorophyll supports production of glucose and oxygen.')
    s += '''<path d="M290 324 C290 241 367 205 432 226 C475 240 510 275 510 311 C490 368 420 397 361 382 C326 374 301 354 290 324 Z" fill="#d9f5d5" stroke="#398c5c" stroke-width="4"/>
<path d="M310 342 C357 323 416 300 484 258 M359 323 L344 286 M395 307 L385 270 M419 299 L445 323" fill="none" stroke="#398c5c" stroke-width="3"/>
'''
    s += f'<circle cx="400" cy="158" r="23" fill="#fbd466" stroke="#e4a92c" stroke-width="3">{pulse(0)}</circle>'
    s += f'<path d="M400 189 V218 M392 210 L400 218 L408 210" stroke="#e4a92c" stroke-width="4" fill="none">{pulse(0)}</path>'
    # Separate paths and arrowheads, avoiding SVG markers and keeping all extents explicit.
    for d, delay in [('M184 264 H281 M270 256 L281 264 L270 272',1), ('M184 364 H281 M270 356 L281 364 L270 372',2), ('M520 264 H615 M604 256 L615 264 L604 272',1), ('M520 364 H615 M604 356 L615 364 L604 372',2)]:
        s += f'<path d="{d}" fill="none" stroke="#5683c0" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{pulse(delay)}</path>'
    s += text(452, 163, 'Light energy', 14, '#966610', 'start', 'bold')
    s += text(400, 415, 'Leaf contains chlorophyll', 15, '#246941', 'middle', 'bold')
    s += text(105, 253, 'Carbon dioxide', 14, '#243851', 'middle', 'bold') + text(105, 353, 'Water', 14, '#243851', 'middle', 'bold')
    s += text(684, 253, 'Oxygen', 14, '#243851', 'middle', 'bold') + text(684, 353, 'Glucose', 14, '#243851', 'middle', 'bold')
    return s + footer('Carbon dioxide + water  →  glucose + oxygen')


def states():
    s = start('States of matter', 'Particle models: spacing and movement', 'Solid particles are closely packed and vibrate; liquid particles are close and move past one another; gas particles are far apart and move freely.')
    colors = ['#507cde','#0da68b','#d9893e']
    for x, label, color in [(50,'SOLID',colors[0]),(293,'LIQUID',colors[1]),(536,'GAS',colors[2])]:
        s += f'<rect x="{x}" y="143" width="214" height="287" rx="15" fill="#f7f9fd" stroke="#e1e7f0" stroke-width="2"/>'
        s += text(x+107,176,label,16,color,'middle','bold')
        s += f'<rect x="{x+20}" y="198" width="174" height="165" rx="8" fill="#ffffff" stroke="#c9d5e4" stroke-width="2"/>'
    for row in range(4):
        for col in range(4):
            x,y=108+col*31,228+row*34
            s += f'<circle cx="{x}" cy="{y}" r="12" fill="{colors[0]}">{pulse((row+col)%3)}</circle>'
    for row in range(4):
        for col in range(4):
            positions = [[(350,228),(381,230),(412,227),(443,231)],
                         [(355,258),(386,262),(418,258),(449,261)],
                         [(349,291),(382,294),(414,289),(445,293)],
                         [(356,323),(388,326),(419,321),(451,325)]]
            x,y=positions[row][col]
            s += f'<circle cx="{x}" cy="{y}" r="12" fill="{colors[1]}">{pulse((row+col)%3)}</circle>'
    for i,(x,y) in enumerate([(571,226),(635,218),(704,237),(601,275),(680,290),(579,331),(641,342),(713,331)]):
        s += f'<circle cx="{x}" cy="{y}" r="11" fill="{colors[2]}">{pulse(i%3)}</circle>'
    s += text(157,392,'Close, ordered',14,'#435875','middle','bold') + text(157,413,'Vibrate in place',13,'#52637a','middle')
    s += text(400,392,'Close, irregular',14,'#435875','middle','bold') + text(400,413,'Move past each other',13,'#52637a','middle')
    s += text(643,392,'Far apart',14,'#435875','middle','bold') + text(643,413,'Move freely and fast',13,'#52637a','middle')
    s += text(400, 474, 'Pulsing highlights the particles; it does not depict their paths.', 14, '#52637a','middle')
    return s + footer('Heating can change how particles are arranged and move')


REASONS = [
    'The 3–4–5 triangle is right-angled; the side squares have areas 9, 16 and 25 square units, with 9 + 16 = 25.',
    'The diameter passes through the centre; the radius joins the centre to the circumference, and the diameter is twice the radius.',
    'The wires connect each cell terminal to both lamps in one closed loop; the current is the same throughout and the lamp voltages sum to the cell voltage.',
    'Carbon dioxide and water are inputs; chlorophyll absorbs light, and glucose and oxygen are products. The word equation is simplified.',
    'Solid particles are closely packed and ordered; liquid particles are close and irregular; gas particles are widely separated. Captions describe the motion.',
]


def main():
    diagrams = [pythagoras(), circle(), circuit(), photosynthesis(), states()]
    results = []
    for concept, svg, reason in zip(CONCEPTS, diagrams, REASONS):
        review = {'status': 'pass', 'reason': reason, 'svg_sha256': svg_digest(svg),
                  'method': 'AI assistant assessment of SVG geometry, labels and rendered layout; not independent expert or user approval.'}
        result = assess_result({'id': concept['id'], 'name': concept['name'], 'subject': concept['subject'],
            'svg': svg, 'model': 'Built-in illustration', 'input_tokens': 0, 'output_tokens': 0,
            'cost_usd': 0, 'validation_retries': 0, 'api_retries': 0, 'latency_seconds': 0,
            'note': 'Built-in example; no Gemini request was made.', 'scientific_verification': review}, concept)
        results.append(result)
    (ROOT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for result in results:
        print(result['id'], result['final_status'], [(k, v['reason']) for k, v in result['checks'].items() if v['passed'] is not True])


if __name__ == '__main__':
    main()
