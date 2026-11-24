# concepts.py
# The 5 science concepts from the assignment, with the EXACT text given to the model,
# plus the keywords a correct diagram must contain (used by the keyword check).
# Concept 1 also has a "layout_hint": exact coordinates and animation steps,
# because the model kept drawing the hypotenuse square in the wrong place.

CONCEPTS = [
    {
        "id": 1,
        "name": "Pythagoras' theorem",
        "subject": "Maths",
        "text": (
            "In a right-angled triangle, the longest side is called the hypotenuse. "
            "The square of the hypotenuse is equal to the sum of the squares of the "
            "other two sides: a² + b² = c²."
        ),
        "keywords": ["hypotenuse"],
        "review_hint": "Show a right angle and three squares on the corresponding sides. Use square units for all areas, and avoid overlapping labels.",
        "layout_hint": (
            "Use the following exact polygons, with no transforms, for a 3–4–5 right triangle "
            "(30 drawing units represent one side unit): "
            "triangle: 320,265 320,355 440,355; "
            "square on a: 320,265 320,355 230,355 230,265; "
            "square on b: 320,355 440,355 440,475 320,475; "
            "square on hypotenuse c: 320,265 440,355 530,235 410,145. "
            "Draw the right-angle marker inside the triangle at (320,355). "
            "Place centered area labels in their squares: a² = 9 at (275,304), "
            "b² = 16 at (380,410), c² = 25 at (425,245), with separate "
            "'square units' labels below. Label the triangle sides 3 and 4 and "
            "identify the hypotenuse as c = 5 without covering any other label. "
            "Caption: a² + b² = c² and 9 + 16 = 25. Pulse the squares in sequence."
        ),
    },
    {
        "id": 2,
        "name": "Parts of a circle",
        "subject": "Maths",
        "text": (
            "A circle has a centre. The radius is the distance from the centre to the edge. "
            "The diameter goes across the circle through the centre and is twice the radius. "
            "The circumference is the distance around the circle."
        ),
        "keywords": ["centre", "radius", "diameter", "circumference"],
        "review_hint": "Draw a radius from the centre to the edge and a diameter across the centre equal to twice the radius; distinguish the circumference.",
        "layout_hint": ("Use a circle centred at (260,300), radius 150. Draw the diameter "
                        "from (110,300) to (410,300) and a distinct radius from (260,300) "
                        "to (350,180), which lies on the circumference. Put a colour-coded "
                        "legend on the right, and pulse the circle and line highlights."),
    },
    {
        "id": 3,
        "name": "Series circuit",
        "subject": "Physics",
        "text": (
            "In a series circuit there is only one loop. The current is the same everywhere "
            "in the loop. The voltage of the cell is shared between the components."
        ),
        "keywords": ["cell", "current", "voltage"],
        "review_hint": "Draw a single closed loop with the cell and two lamps electrically connected in series. Every wire must meet a component terminal; never leave a gap. Show the same current and the shared voltage.",
        "layout_hint": ("Use two standard lamp symbols (a circle with a cross) centred at "
                        "(320,255) and (480,255), radius 30. Join the wire exactly to their "
                        "left and right edges. Use the path M200 335 V255 H290 M350 255 H450 "
                        "M510 255 H640 V430 H200 V365. Draw the cell as horizontal plates "
                        "at y=335 and y=365, each crossing x=200, with the longer plate "
                        "positive. The plates represent the cell, not a broken wire. "
                        "Label cell, current, voltage and both lamps; show conventional "
                        "current arrows clockwise and Vcell = V1 + V2. Pulse arrows only "
                        "as highlights, not as a simulation of moving charge."),
    },
    {
        "id": 4,
        "name": "Photosynthesis",
        "subject": "Biology",
        "text": (
            "Plants take in carbon dioxide and water. They use light energy, absorbed by "
            "chlorophyll, to make glucose and oxygen."
        ),
        "keywords": ["chlorophyll", "glucose", "oxygen", "carbon dioxide"],
        "review_hint": "Show water and carbon dioxide entering the leaf, light absorbed by chlorophyll, and glucose and oxygen as products; use clear arrows.",
        "layout_hint": ("Place a leaf in the centre; arrows from the left carry carbon dioxide "
                        "and water into it, a light-energy arrow points down into the leaf, "
                        "and arrows on the right point outward to glucose and oxygen. Label "
                        "chlorophyll in the leaf. Pulse the arrows as highlights. Show the "
                        "word equation as a simplified summary, without implying light is matter."),
    },
    {
        "id": 5,
        "name": "States of matter",
        "subject": "Chemistry",
        "text": (
            "In a solid the particles are close together and vibrate in place. "
            "In a liquid they are close but move past each other. "
            "In a gas they are far apart and move fast."
        ),
        "keywords": ["solid", "liquid", "gas"],
        "review_hint": "Show closely packed solid particles vibrating, closely packed liquid particles moving past each other, and widely spaced fast gas particles within their containers.",
        "layout_hint": ("Use three labelled, equally sized panels. Show many close, ordered "
                        "particles in the solid; close, irregular particles in the liquid; "
                        "and fewer, widely spaced particles in the gas. Keep all particles "
                        "inside their containers. Label solid vibrations, liquid particles "
                        "moving past each other and fast gas motion. If particles merely pulse, "
                        "say the pulse highlights them rather than depicting their paths."),
    },
]


def get_concept(concept_id):
    """Return the concept dict with this id, or None if it doesn't exist."""
    for concept in CONCEPTS:
        if concept["id"] == concept_id:
            return concept
    return None