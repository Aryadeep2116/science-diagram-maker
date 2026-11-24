# prompts.py
# Builds the text we send to the model. Two versions:
#   1) the first-attempt prompt
#   2) the retry prompt, which also tells the model exactly what went wrong

import config


def build_prompt(concept):
    """Make the first-attempt prompt for one concept."""
    # Each line is one clear rule; models follow short explicit rules better.
    return f"""You are an expert science teacher and SVG artist.
Create ONE animated SVG diagram for UK GCSE students about this concept.

Subject: {concept['subject']}
Concept: {concept['name']}
Explanation: {concept['text']}

STRICT RULES:
1. Reply with SVG code ONLY. No markdown fences, no explanation text.
2. The root tag must be exactly: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {config.VIEWBOX_WIDTH} {config.VIEWBOX_HEIGHT}">
3. Include a <title> element as a child of <svg> naming the concept.
4. Include at least 5 clear <text> labels using the key terms from the explanation.
5. Keep EVERYTHING (shapes and text) inside the viewBox, with a margin of at least 20 units.
6. Use font-size of 14 or larger so text is readable.
7. Include meaningful looping animation that illustrates the idea
   (for example: moving current dots, vibrating particles, a pulsing shape).
   Use SMIL (<animate>, <animateTransform>, <animateMotion>) or CSS @keyframes.
8. Do NOT use <script>, <foreignObject>, event attributes (onclick etc.) or external links/images.
9. Keep the design clean and simple with good colour contrast on a light background.
"""


def build_retry_prompt(concept, failures):
    """Make the retry prompt.

    failures is a list of (check_name, reason) pairs for the checks that failed.
    We append them so the model knows exactly what to fix.
    """
    base = build_prompt(concept)              # start with the original instructions

    problem_lines = []                        # collect one line per failed check
    for check_name, reason in failures:
        problem_lines.append(f"- {check_name}: {reason}")
    problems = "\n".join(problem_lines)

    return (
        base
        + "\nYOUR PREVIOUS ATTEMPT WAS REJECTED by automatic checks. Problems found:\n"
        + problems
        + "\n\nFix ALL of these problems and return the complete corrected SVG only."
    )