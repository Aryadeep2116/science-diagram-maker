# concepts.py
# The 5 science concepts from the assignment, with the EXACT text given to the model,
# plus the keywords a correct diagram must contain (used by the keyword check later).
# Concept 1 also has a "layout_hint": exact coordinates, because the model
# kept drawing the hypotenuse square in the wrong place.

CONCEPTS = [
    {
        "id": 1,                                   # unique number, used in URLs and localStorage
        "name": "Pythagoras' theorem",
        "subject": "Maths",
        "text": (
            "In a right-angled triangle, the longest side is called the hypotenuse. "
            "The square of the hypotenuse is equal to the sum of the squares of the "
            "other two sides: a² + b² = c²."
        ),
        "keywords": ["hypotenuse"],                # words that must appear in the diagram's labels
        # Fixed coordinates for a 3-4-5 triangle (sides 90, 120, 150), no transforms needed.
                "layout_hint": (
            "Use EXACTLY these polygons (a 3-4-5 right triangle, no transforms):\n"
            "- Triangle: points=\"320,290 320,380 440,380\" (right angle at 320,380)\n"
            "- Square on the vertical side a (left): points=\"320,290 320,380 230,380 230,290\"\n"
            "- Square on the horizontal side b (below): points=\"320,380 440,380 440,500 320,500\"\n"
            "- Square on the hypotenuse c (up and right): points=\"320,290 440,380 530,260 410,170\"\n"
            "- Right-angle marker: points=\"320,380 340,380 340,360 320,360\"\n"
            "Labels: 'a' at (275,340), 'b' at (380,445), 'Hypotenuse c' at (425,275), "
            "title at y=45, subtitle at y=68, formula 'a² + b² = c²' at (400,560).\n"
            "\nREQUIRED ANIMATION: one looping story, 9 seconds, repeatCount=\"indefinite\", "
            "using SMIL <animate> with keyTimes so it loops smoothly. Every shape and label "
            "must stay visible at the end of each loop.\n"
            "1. 0s-2s: the square on side a fades in (fill-opacity 0.1 to 0.8) and its label 'a² = 9 units' appears.\n"
            "2. 2s-4s: the square on side b does the same, with the label 'b² = 16 units'.\n"
            "3. 4s-6s: the square on the hypotenuse fades in (fill-opacity 0.1 to 0.8) and its label 'c² = 25 units' appears.\n"
            "4. 6s-8s: the three squares pulse together (stroke-width 2 to 5 and back) while the formula "
            "'a² + b² = c²' fades in and a dot travels along the hypotenuse using <animateMotion> "
            "with an absolute path 'M320,290 L440,380'.\n"
            "5. 8s-9s: hold, then restart.\n"
            "Use different colours for a, b and c. Do not use transform attributes."
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
    },
]


def get_concept(concept_id):
    """Return the concept dict with this id, or None if it doesn't exist."""
    for concept in CONCEPTS:               # simple loop, easy to explain
        if concept["id"] == concept_id:
            return concept
    return None