# concepts.py
# The 5 science concepts from the assignment, with the EXACT text given to the model,
# plus the keywords a correct diagram must contain (used by the keyword check later).

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